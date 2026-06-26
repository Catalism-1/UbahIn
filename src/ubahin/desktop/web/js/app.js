/* Ubahin desktop frontend runtime.
 * Calls the pywebview bridge as `window.pywebview.api.<method>(...)`.
 * Backend dispatches DOM events via window.__ubahinDispatch(name, payload).
 */
'use strict';

const Ubahin = (() => {
  // ---------- state ----------
  const state = {
    files: [],
    settings: {
      theme: 'system',
      default_output_dir: '',
      performance_mode: 'seimbang',
      default_jpg_quality: 90,
      default_dpi: 200,
      notify_on_completion: true,
      open_output_after_finish: true,
      auto_zip_after_finish: false,
    },
    folder: '',
    pdfStage: 'empty', // empty | queue | processing | done
    quality: 'Tinggi',
    dpi: 200,
    jpgQuality: 90,
    optimize: true,
    makeZip: false,
    openAfter: true,
    sidebarCollapsed: false,
    currentScreen: 'beranda',
    activeJob: null,    // { jobId, startedAt, filesTotal, pagesTotal, current: {file, page, total}, log: Map }
    lastDone: null,     // { fileCount, totalImages, durationSec, folder }
    histFilter: 'semua',
    appInfo: null,
    pendingConfirm: null,
  };

  // ---------- DOM helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const el = (tag, attrs = {}, children = []) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') node.className = v;
      else if (k === 'html') node.innerHTML = v;
      else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) node.setAttribute(k, v);
    }
    for (const child of [].concat(children)) {
      if (child == null) continue;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
  };

  const formatBytes = (bytes) => {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    let v = bytes; let i = 0;
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${u[i]}`;
  };

  const formatDuration = (sec) => {
    if (!Number.isFinite(sec) || sec < 0) return '—';
    const m = Math.floor(sec / 60);
    const s = Math.round(sec - m * 60);
    if (m === 0) return `${s} detik`;
    return `${m} menit ${s} detik`;
  };

  const tints = ['tone-blue', 'tone-sage', 'tone-lavender', 'tone-peach', 'tone-pink'];

  // ---------- bridge ----------
  const bridge = {
    ready() {
      return !!(window.pywebview && window.pywebview.api);
    },
    async waitReady(timeoutMs = 5000) {
      const start = Date.now();
      while (!this.ready()) {
        if (Date.now() - start > timeoutMs) throw new Error('Bridge tidak tersedia.');
        await new Promise(r => setTimeout(r, 50));
      }
    },
    async call(name, ...args) {
      await this.waitReady();
      try {
        const result = await window.pywebview.api[name](...args);
        return result;
      } catch (err) {
        console.error('[bridge]', name, err);
        throw err;
      }
    },
  };

  // ---------- toast / modal ----------
  let toastTimer = null;
  const showToast = (msg, type = 'info') => {
    const node = $('#toast');
    if (!node) return;
    node.className = `toast ${type}`;
    $('#toast-msg').textContent = msg;
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { node.hidden = true; }, 2600);
  };

  const askConfirm = ({ title, body, confirmText = 'Ya, hapus' }) => {
    return new Promise((resolve) => {
      $('#modal-title').textContent = title;
      $('#modal-body').textContent = body;
      $('#modal-confirm').textContent = confirmText;
      $('#modal-mask').hidden = false;
      state.pendingConfirm = resolve;
    });
  };

  const closeModal = (result) => {
    $('#modal-mask').hidden = true;
    if (state.pendingConfirm) {
      const r = state.pendingConfirm;
      state.pendingConfirm = null;
      r(result);
    }
  };

  // ---------- routing ----------
  const SCREEN_TITLES = {
    beranda: ['Beranda', 'Ringkasan & alat cepat'],
    pdf: ['Ubah PDF', 'Konversi file PDF'],
    gambar: ['Ubah Gambar', 'Alat untuk gambar'],
    riwayat: ['Riwayat', 'Aktivitas konversimu'],
    pengaturan: ['Pengaturan', 'Atur aplikasi'],
    sistem: ['Pemeriksaan Sistem', 'Status komponen Ubahin'],
    tentang: ['Tentang Ubahin', 'Versi & informasi'],
  };

  const showScreen = (screen) => {
    state.currentScreen = screen;
    $$('.nav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.screen === screen);
    });
    const sub = screen === 'pdf' ? `pdf-${state.pdfStage}` : screen;
    $$('.screen').forEach(node => {
      node.classList.toggle('active', node.dataset.screen === sub);
    });
    const [title, crumb] = SCREEN_TITLES[screen] || ['Ubahin', ''];
    $('#topbar-title').textContent = title;
    $('#topbar-crumb').textContent = crumb;
    if (screen === 'riwayat') renderHistory();
    if (screen === 'sistem') runSystemCheck();
    if (screen === 'beranda') renderRecents();
  };

  // ---------- file queue ----------
  const renderQueue = () => {
    const list = $('#file-list');
    list.innerHTML = '';
    state.files.forEach((f, i) => {
      const ico = el('span', { class: `file-ico ${tints[i % tints.length]}` });
      ico.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"></path><path d="M14 3v5h5"></path></svg>';

      const meta = el('div', { class: 'file-meta' }, [
        el('div', { class: 'file-name' }, f.name),
        el('div', { class: 'file-info' }, `${formatBytes(f.size)} · ${f.pages} halaman`),
      ]);

      let badge;
      if (f.status === 'failed') {
        badge = el('span', { class: 'file-status err' }, [el('span', { class: 'dot' }), 'Gagal']);
      } else if (f.status === 'completed') {
        badge = el('span', { class: 'file-status' }, [el('span', { class: 'dot' }), 'Selesai']);
      } else if (f.status === 'processing') {
        badge = el('span', { class: 'file-status warn' }, [el('span', { class: 'dot' }), 'Memproses']);
      } else {
        badge = el('span', { class: 'file-status' }, [el('span', { class: 'dot' }), 'Siap diubah']);
      }

      const remove = el('button', { class: 'file-remove', title: 'Hapus file', onclick: () => removeFile(f.id) });
      remove.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path></svg>';

      list.appendChild(el('div', { class: 'file-row' }, [ico, meta, badge, remove]));
    });

    const count = state.files.length;
    const pages = state.files.reduce((a, f) => a + (f.pages || 0), 0);
    $('#queue-count').textContent = count;
    $('#queue-pages').textContent = pages;
    $('#est-files').textContent = `${count} file`;
    $('#est-pages').textContent = `${pages} halaman`;
    $('#est-images').textContent = `± ${pages} JPG`;
    const estMB = Math.max(1, Math.round(pages * 0.18));
    $('#est-size').textContent = `± ${estMB} MB`;
    $('#queue-start').disabled = count === 0;
  };

  const removeFile = async (fileId) => {
    state.files = state.files.filter(f => f.id !== fileId);
    if (state.files.length === 0) {
      state.pdfStage = 'empty';
      showScreen('pdf');
    } else {
      renderQueue();
    }
    try { await bridge.call('remove_selected_file', fileId); } catch (_) {}
  };

  const clearFiles = async () => {
    if (state.files.length === 0) return;
    const ok = await askConfirm({
      title: 'Hapus semua file?',
      body: 'Semua file dalam antrean akan dikeluarkan. Tindakan ini tidak bisa dibatalkan.',
      confirmText: 'Ya, hapus',
    });
    if (!ok) return;
    state.files = [];
    state.pdfStage = 'empty';
    showScreen('pdf');
    try { await bridge.call('clear_selected_files'); } catch (_) {}
    showToast('Semua file dihapus', 'info');
  };

  const pickFiles = async () => {
    try {
      const result = await bridge.call('select_pdf_files');
      if (!result || !result.success) {
        if (result && result.message) showToast(result.message, 'error');
        return;
      }
      const incoming = result.data?.files || [];
      if (incoming.length === 0) return;
      const seen = new Set(state.files.map(f => f.id));
      for (const f of incoming) if (!seen.has(f.id)) state.files.push(f);
      if (state.files.length > 50) {
        state.files = state.files.slice(0, 50);
        showToast('Maksimal 50 file. File berlebih diabaikan.', 'warning');
      }
      state.pdfStage = 'queue';
      showScreen('pdf');
      renderQueue();
    } catch (err) {
      showToast('Tidak dapat membuka pemilih file.', 'error');
    }
  };

  // ---------- folder picker ----------
  const pickFolder = async (target = 'queue') => {
    try {
      const result = await bridge.call('select_output_folder');
      if (!result || !result.success) return;
      const folder = result.data?.folder;
      if (!folder) return;
      state.folder = folder;
      $('#folder-path').textContent = folder;
      $('#settings-folder').textContent = folder;
      if (target === 'settings') {
        state.settings.default_output_dir = folder;
        await bridge.call('save_settings', state.settings);
        showToast('Folder hasil default disimpan', 'success');
      }
    } catch (err) {
      showToast('Tidak dapat membuka pemilih folder.', 'error');
    }
  };

  // ---------- conversion ----------
  const startJob = async () => {
    if (state.files.length === 0) return;
    if (!state.folder) {
      showToast('Pilih folder hasil terlebih dahulu.', 'warning');
      return;
    }
    state.lastDone = null;
    state.activeJob = {
      jobId: null,
      startedAt: Date.now(),
      filesTotal: state.files.length,
      pagesTotal: state.files.reduce((a, f) => a + (f.pages || 0), 0),
      current: { file: state.files[0]?.name || '', page: 0, total: 0 },
      log: new Map(state.files.map(f => [f.name, 'queued'])),
    };
    state.pdfStage = 'processing';
    showScreen('pdf');
    renderProcessing(0);
    renderLog();

    const payload = {
      files: state.files.map(f => f.id),
      output_folder: state.folder,
      preset: state.quality,
      dpi: state.dpi,
      jpg_quality: state.jpgQuality,
      optimize_size: state.optimize,
      create_zip: state.makeZip,
      open_after_finish: state.openAfter,
      performance_mode: state.settings.performance_mode || 'seimbang',
    };

    try {
      const result = await bridge.call('start_pdf_to_jpg_job', payload);
      if (!result || !result.success) {
        state.pdfStage = 'queue';
        showScreen('pdf');
        showToast(result?.message || 'Tidak dapat memulai konversi.', 'error');
        return;
      }
      state.activeJob.jobId = result.data?.job_id || null;
    } catch (err) {
      state.pdfStage = 'queue';
      showScreen('pdf');
      showToast('Tidak dapat memulai konversi.', 'error');
    }
  };

  const cancelJob = async () => {
    if (!state.activeJob || !state.activeJob.jobId) return;
    try {
      await bridge.call('cancel_job', state.activeJob.jobId);
    } catch (_) {}
  };

  const renderProcessing = (pct) => {
    const value = Math.max(0, Math.min(100, Math.round(pct)));
    $('#proc-pct').textContent = `${value}%`;
    $('#proc-bar').style.width = `${value}%`;
    const job = state.activeJob;
    if (!job) return;
    const filesDone = [...job.log.values()].filter(s => s === 'completed' || s === 'failed').length;
    $('#proc-files-done').textContent = filesDone;
    $('#proc-files-total').textContent = job.filesTotal;
    const elapsed = (Date.now() - job.startedAt) / 1000;
    const eta = value > 2 ? Math.max(1, Math.round((elapsed / value) * (100 - value))) : null;
    $('#proc-eta').textContent = eta != null ? formatDuration(eta) : '—';
    $('#proc-current-name').textContent = job.current.file || '—';
    $('#proc-page-cur').textContent = job.current.page || 0;
    $('#proc-page-tot').textContent = job.current.total || 0;
    const filePct = job.current.total > 0 ? Math.round((job.current.page / job.current.total) * 100) : 0;
    $('#proc-file-bar').style.width = `${filePct}%`;
  };

  const renderLog = () => {
    const body = $('#proc-log-body');
    body.innerHTML = '';
    const job = state.activeJob;
    if (!job) return;
    for (const [name, status] of job.log.entries()) {
      const cls = status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : status === 'processing' ? 'processing' : 'queued';
      const text = status === 'completed' ? 'Selesai' : status === 'failed' ? 'Gagal' : status === 'processing' ? 'Memproses…' : 'Menunggu';
      body.appendChild(el('div', { class: `proc-log-row ${cls}` }, [
        el('span', { class: 'ldot' }),
        el('span', { class: 'lname' }, name),
        el('span', { class: 'lstat' }, text),
      ]));
    }
  };

  // ---------- backend events ----------
  const events = {
    job_started(payload) {
      if (!state.activeJob) return;
      state.activeJob.jobId = payload.job_id || state.activeJob.jobId;
      renderProcessing(0);
    },
    progress(payload) {
      if (!state.activeJob) return;
      const pct = Number(payload.overall_percent) || 0;
      const job = state.activeJob;
      job.current.file = payload.current_file || job.current.file;
      job.current.page = payload.current_page || 0;
      job.current.total = payload.total_pages || 0;
      if (job.current.file && job.log.get(job.current.file) !== 'completed' && job.log.get(job.current.file) !== 'failed') {
        job.log.set(job.current.file, 'processing');
      }
      renderProcessing(pct);
      renderLog();
    },
    file_completed(payload) {
      if (!state.activeJob) return;
      if (payload.filename) state.activeJob.log.set(payload.filename, 'completed');
      renderLog();
    },
    file_failed(payload) {
      if (!state.activeJob) return;
      if (payload.filename) state.activeJob.log.set(payload.filename, 'failed');
      renderLog();
      showToast(`Gagal: ${payload.filename || 'file tidak diketahui'}`, 'error');
    },
    job_completed(payload) {
      finishJob(payload, 'completed');
    },
    job_failed(payload) {
      const job = state.activeJob;
      state.activeJob = null;
      state.pdfStage = 'queue';
      showScreen('pdf');
      showToast(payload?.message || 'Konversi gagal.', 'error');
    },
    job_cancelled(payload) {
      state.activeJob = null;
      state.pdfStage = 'queue';
      showScreen('pdf');
      showToast('Proses dibatalkan', 'info');
    },
    warning(payload) {
      if (payload && payload.message) showToast(payload.message, 'warning');
    },
  };

  const finishJob = (payload, kind) => {
    const job = state.activeJob;
    if (!job) return;
    const totalOutputs = Number(payload.total_outputs ?? payload.output_count ?? 0);
    const fileCount = Number(payload.completed_files ?? job.filesTotal);
    const durationSec = (Date.now() - job.startedAt) / 1000;
    state.lastDone = {
      fileCount,
      totalImages: totalOutputs || job.pagesTotal,
      durationSec,
      folder: payload.output_folder || state.folder,
      warnings: payload.warnings || [],
    };
    state.activeJob = null;
    state.pdfStage = 'done';
    showScreen('pdf');
    renderDone();
    if (kind === 'completed') {
      showToast(`Konversi selesai — ${state.lastDone.totalImages} gambar siap`, 'success');
    }
  };

  const renderDone = () => {
    const d = state.lastDone || { fileCount: 0, totalImages: 0, durationSec: 0, folder: '' };
    $('#done-files').textContent = `${d.fileCount} file`;
    $('#done-images').textContent = `${d.totalImages} gambar`;
    $('#done-time').textContent = formatDuration(d.durationSec);
    $('#done-folder').textContent = d.folder || '—';
    $('#done-folder').title = d.folder || '';
  };

  // ---------- history ----------
  const renderHistory = async () => {
    const list = $('#hist-list');
    list.innerHTML = '<div class="empty-row">Memuat riwayat…</div>';
    let items = [];
    try {
      const r = await bridge.call('get_recent_history', 100);
      items = r?.data?.items || [];
    } catch (_) {}

    const f = state.histFilter;
    const filtered = items.filter(it => {
      if (f === 'semua') return true;
      if (f === 'berhasil') return it.status === 'completed' || it.status === 'completed_with_warnings';
      return it.status === 'failed' || it.status === 'cancelled';
    });

    list.innerHTML = '';
    if (filtered.length === 0) {
      list.appendChild(el('div', { class: 'empty-row' }, 'Belum ada riwayat konversi.'));
      return;
    }
    filtered.forEach((it, i) => {
      const ico = el('span', { class: `file-ico ${tints[i % tints.length]}`, style: 'width:38px;height:38px;border-radius:10px;' });
      ico.innerHTML = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"></path><path d="M14 3v5h5"></path></svg>';
      const ok = (it.status === 'completed' || it.status === 'completed_with_warnings');
      const dateText = it.finished_at ? new Date(it.finished_at).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) : '';
      const meta = el('div', { class: 'file-meta' }, [
        el('div', { class: 'file-name' }, it.main_file || it.tool_type || 'Konversi'),
        el('div', { class: 'file-info' }, `${(it.tool_type || '').replace('_', ' → ').toUpperCase()} · ${it.output_count || 0} hasil`),
      ]);
      const status = el('span', { class: `file-status ${ok ? '' : 'err'}` }, [el('span', { class: 'dot' }), ok ? 'Berhasil' : 'Gagal']);
      const date = el('span', { class: 'file-info', style: 'flex:0 0 auto;color:var(--text3)' }, dateText);
      const open = el('button', { class: 'file-remove', title: 'Buka folder hasil', onclick: () => bridge.call('open_output_folder', it.output_dir).catch(() => {}) });
      open.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>';
      list.appendChild(el('div', { class: 'file-row' }, [ico, meta, date, status, open]));
    });
  };

  const renderRecents = async () => {
    const list = $('#beranda-recents');
    list.innerHTML = '<div class="empty-row" id="beranda-recents-empty">Memuat…</div>';
    let items = [];
    try {
      const r = await bridge.call('get_recent_history', 3);
      items = r?.data?.items || [];
    } catch (_) {}
    list.innerHTML = '';
    if (items.length === 0) {
      list.appendChild(el('div', { class: 'empty-row' }, 'Belum ada konversi yang tercatat.'));
      return;
    }
    items.forEach((it, i) => {
      const ico = el('span', { class: `file-ico ${tints[i % tints.length]}`, style: 'width:34px;height:34px;border-radius:9px;' });
      ico.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"></path><path d="M14 3v5h5"></path></svg>';
      const meta = el('div', { class: 'file-meta' }, [
        el('div', { class: 'file-name' }, it.main_file || 'Konversi'),
        el('div', { class: 'file-info' }, `${(it.tool_type || '').replaceAll('_', ' ')} · ${it.output_count || 0} hasil`),
      ]);
      const date = el('span', { class: 'file-info', style: 'flex:0 0 auto;color:var(--text3)' }, it.finished_at ? new Date(it.finished_at).toLocaleDateString('id-ID', { dateStyle: 'medium' }) : '');
      const open = el('button', { class: 'file-remove', title: 'Buka folder hasil', onclick: () => bridge.call('open_output_folder', it.output_dir).catch(() => {}) });
      open.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>';
      list.appendChild(el('div', { class: 'file-row' }, [ico, meta, date, open]));
    });
  };

  // ---------- system check ----------
  const runSystemCheck = async () => {
    const checks = $('#sys-checks');
    checks.innerHTML = '<div class="empty-row" style="padding:14px 0">Sedang memeriksa…</div>';
    try {
      const r = await bridge.call('get_system_check');
      const data = r?.data || {};
      $('#sys-app-data').textContent = data.app_data_dir || '—';
      $('#sys-disk').textContent = data.disk_free ? `${formatBytes(data.disk_free)} bebas` : '—';
      const nativeOn = !!data.native?.available;
      $('#sys-native').textContent = nativeOn ? `Aktif (${data.native.backend || 'rust'})` : 'Fallback Python';
      const badge = $('#sys-native-badge');
      badge.textContent = nativeOn ? 'Aktif' : 'Fallback';
      badge.className = `badge-soft ${nativeOn ? '' : 'warn'}`;
      const diskBadge = $('#sys-disk-badge');
      diskBadge.textContent = data.disk_ok ? 'OK' : 'Periksa';
      diskBadge.className = `badge-soft ${data.disk_ok ? '' : 'warn'}`;
      checks.innerHTML = '';
      (data.checks || []).forEach(c => {
        checks.appendChild(el('div', { class: `check-row ${c.ok ? '' : 'bad'}` }, [
          el('span', { class: 'cdot' }),
          el('span', { class: 'cname' }, c.name),
          el('span', { class: 'cmsg' }, c.message || (c.ok ? 'OK' : 'Periksa')),
        ]));
      });
    } catch (err) {
      checks.innerHTML = `<div class="empty-row" style="padding:14px 0;color:var(--error)">Tidak dapat memuat hasil pemeriksaan.</div>`;
    }
  };

  // ---------- settings / theme ----------
  const applyTheme = (theme) => {
    let actual = theme;
    if (theme === 'system') {
      actual = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', actual);
    const label = $('.theme-label');
    if (label) label.textContent = actual === 'dark' ? 'Mode terang' : 'Mode gelap';
  };

  const setSegmented = (group, value) => {
    $$(`[data-segmented="${group}"] button`).forEach(btn => {
      btn.classList.toggle('active', btn.dataset.value === value);
    });
  };

  const loadSettings = async () => {
    try {
      const r = await bridge.call('get_settings');
      if (r && r.success && r.data) {
        Object.assign(state.settings, r.data);
      }
    } catch (_) {}

    state.folder = state.settings.default_output_dir || '';
    state.dpi = state.settings.default_dpi || 200;
    state.jpgQuality = state.settings.default_jpg_quality || 90;
    state.optimize = true;
    state.openAfter = !!state.settings.open_output_after_finish;
    state.makeZip = !!state.settings.auto_zip_after_finish;

    $('#folder-path').textContent = state.folder || 'Pilih folder hasil…';
    $('#settings-folder').textContent = state.folder || 'Belum dipilih';
    $('#jpg-q-value').textContent = `${state.jpgQuality}%`;
    $('#jpg-quality').value = state.jpgQuality;

    setSegmented('dpi', String(state.dpi));
    setSegmented('theme', state.settings.theme || 'system');
    setSegmented('perf', state.settings.performance_mode || 'seimbang');

    $('[data-toggle="optimize"]').classList.toggle('on', state.optimize);
    $('[data-toggle="zip"]').classList.toggle('on', state.makeZip);
    $('[data-toggle="open"]').classList.toggle('on', state.openAfter);
    $('[data-toggle="notify"]').classList.toggle('on', !!state.settings.notify_on_completion);
    $('[data-toggle="open-after"]').classList.toggle('on', state.openAfter);
    $('[data-toggle="auto-zip"]').classList.toggle('on', state.makeZip);

    applyTheme(state.settings.theme || 'system');
  };

  const saveSettings = async () => {
    try { await bridge.call('save_settings', state.settings); } catch (_) {}
  };

  // ---------- wiring ----------
  const wireEvents = () => {
    $$('.nav-btn').forEach(btn => btn.addEventListener('click', () => showScreen(btn.dataset.screen)));
    $('#sidebar-toggle').addEventListener('click', () => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      $('#sidebar').classList.toggle('collapsed', state.sidebarCollapsed);
    });

    $('#theme-toggle').addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      state.settings.theme = next;
      setSegmented('theme', next);
      applyTheme(next);
      saveSettings();
    });

    $$('.tool-card').forEach(card => {
      card.addEventListener('click', () => {
        const action = card.dataset.action;
        if (action === 'go-pdf') showScreen('pdf');
        else if (action === 'go-gambar') showScreen('gambar');
        else if (action === 'go-riwayat') showScreen('riwayat');
        else if (action === 'coming-soon') showToast('Fitur ini segera hadir', 'info');
      });
    });
    $('.link-btn[data-action="go-riwayat"]').addEventListener('click', () => showScreen('riwayat'));

    $('#pdf-pick').addEventListener('click', pickFiles);
    $('#queue-add').addEventListener('click', pickFiles);
    $('#folder-pick').addEventListener('click', () => pickFolder('queue'));
    $('#settings-folder-pick').addEventListener('click', () => pickFolder('settings'));
    $('#queue-clear-all').addEventListener('click', clearFiles);
    $('#queue-start').addEventListener('click', startJob);
    $('#proc-cancel').addEventListener('click', cancelJob);
    $('#done-again').addEventListener('click', () => {
      state.pdfStage = 'empty';
      state.files = [];
      showScreen('pdf');
    });
    $('#done-open').addEventListener('click', () => {
      const f = state.lastDone?.folder;
      if (f) bridge.call('open_output_folder', f).catch(() => {});
    });

    $('#proc-log-toggle').addEventListener('click', () => {
      $('.proc-log').classList.toggle('collapsed');
    });

    $('#modal-cancel').addEventListener('click', () => closeModal(false));
    $('#modal-confirm').addEventListener('click', () => closeModal(true));
    $('#modal-mask').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeModal(false); });

    $('#jpg-quality').addEventListener('input', (e) => {
      state.jpgQuality = Number(e.target.value);
      $('#jpg-q-value').textContent = `${state.jpgQuality}%`;
    });

    $$('[data-segmented="quality"] button').forEach(btn => btn.addEventListener('click', () => {
      state.quality = btn.dataset.value;
      setSegmented('quality', state.quality);
      const map = { 'Standard': 150, 'Tinggi': 200, 'Sangat Tinggi': 300 };
      state.dpi = map[state.quality] || state.dpi;
      setSegmented('dpi', String(state.dpi));
    }));
    $$('[data-segmented="dpi"] button').forEach(btn => btn.addEventListener('click', () => {
      state.dpi = Number(btn.dataset.value);
      setSegmented('dpi', String(state.dpi));
    }));
    $$('[data-segmented="theme"] button').forEach(btn => btn.addEventListener('click', () => {
      state.settings.theme = btn.dataset.value;
      setSegmented('theme', state.settings.theme);
      applyTheme(state.settings.theme);
      saveSettings();
    }));
    $$('[data-segmented="perf"] button').forEach(btn => btn.addEventListener('click', () => {
      state.settings.performance_mode = btn.dataset.value;
      setSegmented('perf', state.settings.performance_mode);
      saveSettings();
    }));

    document.addEventListener('click', (e) => {
      const toggle = e.target.closest('.toggle');
      if (!toggle) return;
      const name = toggle.dataset.toggle;
      const isOn = toggle.classList.toggle('on');
      if (name === 'optimize') state.optimize = isOn;
      else if (name === 'zip') state.makeZip = isOn;
      else if (name === 'open') state.openAfter = isOn;
      else if (name === 'notify') { state.settings.notify_on_completion = isOn; saveSettings(); }
      else if (name === 'open-after') { state.settings.open_output_after_finish = isOn; state.openAfter = isOn; saveSettings(); }
      else if (name === 'auto-zip') { state.settings.auto_zip_after_finish = isOn; state.makeZip = isOn; saveSettings(); }
    });

    $('#hist-filters').addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      state.histFilter = btn.dataset.filter;
      $$('#hist-filters button').forEach(b => b.classList.toggle('active', b === btn));
      renderHistory();
    });

    $('#sys-rerun').addEventListener('click', runSystemCheck);
    $('#sys-open-log').addEventListener('click', () => bridge.call('open_log_folder').catch(() => {}));
    $('#tentang-open-log').addEventListener('click', () => bridge.call('open_log_folder').catch(() => {}));

    // Custom titlebar — pywebview window controls
    $$('[data-window-action]').forEach(btn => {
      btn.addEventListener('click', () => bridge.call('window_action', btn.dataset.windowAction).catch(() => {}));
    });

    window.addEventListener('ubahin-event', (e) => {
      const { name, payload } = e.detail || {};
      const handler = events[name];
      if (handler) handler(payload || {});
    });
  };

  // Backend → frontend dispatcher (called from Python via evaluate_js)
  window.__ubahinDispatch = (name, payload) => {
    window.dispatchEvent(new CustomEvent('ubahin-event', { detail: { name, payload } }));
  };

  // ---------- init ----------
  const init = async () => {
    wireEvents();
    try {
      await bridge.waitReady(8000);
    } catch (err) {
      const node = el('div', { class: 'empty-row', style: 'padding:32px;text-align:center;color:var(--error)' }, 'Bridge Python tidak tersedia. Periksa folder log Ubahin.');
      $('.content-scroll').prepend(node);
      return;
    }
    try {
      const info = await bridge.call('get_app_info');
      if (info && info.data) {
        state.appInfo = info.data;
        $('#app-version').textContent = `v${info.data.version}`;
        $('#settings-version').textContent = info.data.version;
        $('#tentang-version').textContent = `Versi ${info.data.version}`;
        $('#tentang-logdir').textContent = info.data.log_dir || '';
      }
    } catch (_) {}

    await loadSettings();
    renderQueue();
    showScreen('beranda');
  };

  return { init, events, state };
})();

document.addEventListener('DOMContentLoaded', Ubahin.init);
