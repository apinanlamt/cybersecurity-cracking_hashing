const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
}

function showError(container, error) {
  container.textContent = error.message || 'เกิดข้อผิดพลาด';
}

function appendLog(container, message, color = '') {
  const line = document.createElement('div');
  if (color) line.className = color;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  container.appendChild(line);
  container.scrollTop = container.scrollHeight;
}

async function streamPost(path, data, logContainer, onResult) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'เกิดข้อผิดพลาด');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  while (true) {
    const { value, done } = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = pending.split('\n');
    pending = lines.pop() || '';
    for (const line of lines) {
      if (!line.trim()) continue;
      const item = JSON.parse(line);
      if (item.type === 'log') appendLog(logContainer, item.message);
      if (item.type === 'progress') {
        if (item.data?.algorithm) {
          const outcome = item.data.found ? `พบ ${item.data.found}` : 'ไม่พบ';
          appendLog(logContainer, `${item.data.algorithm}: ${item.data.attempts} attempts, ${outcome}`, 'text-cyan-300');
        } else if (item.data?.index) {
          appendLog(logContainer, `รอบ ${item.data.index}: สร้าง hash ${item.data.hash}`);
        } else if (item.data?.attempts) {
          appendLog(logContainer, `สรุปการค้นหา: ${item.data.attempts.toLocaleString()} attempts ใน ${item.data.milliseconds.toFixed(1)} ms`);
        }
      }
      if (item.type === 'result' && onResult) onResult(item.data);
    }
    if (done) break;
  }
}

function resetLog(container) {
  container.replaceChildren();
}

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.panel').forEach((panel) => panel.classList.remove('active'));
    tab.classList.add('active');
    $(tab.dataset.t).classList.add('active');
  });
});

window.runHashPlayground = async function () {
  const output = $('hp-out');
  const log = $('hp-log');
  resetLog(log);
  output.textContent = 'Python กำลังคำนวณ...';
  try {
    await streamPost('/api/hash', {
      password: $('pw1').value,
      salt: '',
      cost: Number($('costrange').value)
    }, log, (result) => {
      output.innerHTML = `
        <article class="hash-result"><div class="hash-result-header"><h3>MD5</h3><small>${result.md5.milliseconds.toFixed(3)} ms</small><span class="badge b-fast">Fast</span></div><code class="hash-value">${escapeHtml(result.md5.hash)}</code></article>
        <article class="hash-result"><div class="hash-result-header"><h3>SHA-1</h3><small>${result.sha1.milliseconds.toFixed(3)} ms</small><span class="badge b-fast">Fast</span></div><code class="hash-value">${escapeHtml(result.sha1.hash)}</code></article>
        <article class="hash-result"><div class="hash-result-header"><h3>bcrypt · cost ${Number($('costrange').value)}</h3><small>${result.bcrypt.milliseconds.toFixed(1)} ms</small><span class="badge b-slow">Adaptive</span></div><code class="hash-value">${escapeHtml(result.bcrypt.hash)}</code></article>`;
    });
  } catch (error) { showError(output, error); }
};

window.runDictAttack = async function () {
  const output = $('dict-out');
  const log = $('dict-log');
  resetLog(log);
  output.textContent = 'Python กำลังจำลองการโจมตี...';
  try {
    await streamPost('/api/dictionary', {
      target: $('target2').value,
      wordlist: $('wl').value,
      cost: Number($('costrange').value)
    }, log, (result) => {
      output.innerHTML = result.results.map((item) => {
        const slow = item.algorithm === 'bcrypt';
        return `<article class="result-card"><div class="result-card-title"><b>${escapeHtml(item.algorithm)}</b><span class="badge ${slow ? 'b-slow' : 'b-fast'}">${slow ? 'Slow' : 'Fast'}</span></div>
          <p>${item.attempts.toLocaleString()} attempts · ${item.rate.toFixed(0)} guesses/sec</p><strong>${item.found ? `พบ: ${escapeHtml(item.found)}` : 'ไม่พบใน wordlist'}</strong></article>`;
      }).join('');
    });
  } catch (error) { showError(output, error); }
};

async function loadWordlistModal() {
  const content = $('wordlist-modal-content');
  const description = $('wordlist-modal-description');
  const name = $('wl').value;
  const selectedLabel = $('wl').selectedOptions[0].textContent;
  description.textContent = `${selectedLabel} · กำลังโหลดรายการคำจาก Python...`;
  content.textContent = 'กำลังโหลด...';
  try {
    const response = await fetch(`/api/wordlist/${encodeURIComponent(name)}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'โหลด Wordlist ไม่สำเร็จ');
    description.textContent = `${selectedLabel} · ทั้งหมด ${result.count} คำ`;
    const chips = document.createElement('div');
    chips.className = 'wordlist-chips';
    result.words.forEach((word) => {
      const chip = document.createElement('code');
      chip.textContent = word;
      chips.appendChild(chip);
    });
    content.replaceChildren(chips);
  } catch (error) {
    content.textContent = error.message || 'โหลด Wordlist ไม่สำเร็จ';
  }
}

window.openWordlistModal = async function () {
  const modal = $('wordlist-modal');
  if (!modal.open) modal.showModal();
  await loadWordlistModal();
};

$('wl').addEventListener('change', () => {
  if ($('wordlist-modal').open) loadWordlistModal();
});
$('wordlist-modal').addEventListener('click', (event) => {
  const bounds = $('wordlist-modal').getBoundingClientRect();
  const outside = event.clientX < bounds.left || event.clientX > bounds.right ||
    event.clientY < bounds.top || event.clientY > bounds.bottom;
  if (outside) $('wordlist-modal').close();
});

function formatTime(seconds) {
  if (seconds < 1) return `${(seconds * 1000).toFixed(1)} ms`;
  if (seconds < 60) return `${seconds.toFixed(1)} วินาที`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)} นาที`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} ชั่วโมง`;
  if (seconds < 31536000) return `${(seconds / 86400).toFixed(1)} วัน`;
  return `${(seconds / 31536000).toExponential(2)} ปี`;
}

window.runBruteForce = async function () {
  const output = $('brute-out');
  const log = $('brute-log');
  resetLog(log);
  output.textContent = 'Python กำลังประมวลผล...';
  try {
    await streamPost('/api/bruteforce', {
      target: $('target3').value,
      charset: $('charset').value,
      length: Number($('bruteLen').value)
    }, log, (result) => {
      const labels = { MD5: '20,000,000,000 H/s', 'SHA-1': '8,000,000,000 H/s', 'bcrypt (cost 12)': '~15,000 H/s' };
      const real = result.real_result;
      const summary = real
        ? `<div class="metric-grid">
             <article class="metric-card"><span>Attempts</span><strong>${real.attempts.toLocaleString()}</strong></article>
             <article class="metric-card"><span>Hash rate</span><strong>${real.rate.toFixed(0)} H/s</strong></article>
             <article class="metric-card"><span>เวลาที่ใช้</span><strong>${real.milliseconds.toFixed(2)} ms</strong></article>
           </div><p class="brute-outcome">${real.found ? `พบรหัสผ่าน: <strong>${escapeHtml(real.found)}</strong>` : 'ไม่พบรหัสผ่านในขอบเขตทดลองจริง'}</p>`
        : '<p class="brute-outcome">Keyspace ใหญ่เกินขอบเขตทดลองจริง · แสดงเฉพาะการประมาณ</p>';
      output.innerHTML = `${summary}<div class="keyspace-line">Keyspace ทั้งหมด: <strong>${result.keyspace.toLocaleString()}</strong></div>
        <h3 class="estimate-title">เวลาเฉลี่ยคาดการณ์ (GPU estimate)</h3>
        <table><tr><th>Hash</th><th>ความเร็วโดยประมาณ</th><th>เวลาเฉลี่ย</th></tr>${Object.entries(result.estimated_seconds).map(([name, seconds]) => `<tr><td>${escapeHtml(name)}</td><td>${labels[name]}</td><td>${formatTime(seconds)}</td></tr>`).join('')}</table>
        <p class="field-hint">อัตรา GPU เป็นค่าประมาณเพื่อการศึกษา ส่วนผลทดลองจริงรันด้วย Python บนเครื่องนี้</p>`;
    });
  } catch (error) { showError(output, error); }
};

window.runSaltDemo = async function () {
  const output = $('salt-out');
  const log = $('salt-log');
  resetLog(log);
  output.textContent = 'รอผลลัพธ์จาก Python...';
  try {
    await streamPost('/api/salt-demo', {
      password: $('pw4').value,
      cost: Number($('salt-cost').value)
    }, log, (result) => {
      output.innerHTML = result.examples.map((item, index) => `<article class="salt-hash-row"><div><span>รอบ ${index + 1}</span><strong>Salt</strong><code>${escapeHtml(item.salt)}</code></div><div><strong>bcrypt hash</strong><code>${escapeHtml(item.hash)}</code></div></article>`).join('');
    });
  } catch (error) { showError(output, error); }
};

const actions = {
  'hash-playground': window.runHashPlayground,
  dictionary: window.runDictAttack,
  bruteforce: window.runBruteForce,
  'salt-demo': window.runSaltDemo,
  'wordlist-modal': window.openWordlistModal,
  'close-wordlist-modal': () => $('wordlist-modal').close()
};
document.querySelectorAll('[data-action]').forEach((button) => {
  button.addEventListener('click', actions[button.dataset.action]);
});
$('costrange').addEventListener('input', (event) => {
  $('costval').textContent = event.currentTarget.value;
});
$('salt-cost').addEventListener('input', (event) => {
  $('salt-cost-val').textContent = event.currentTarget.value;
});
