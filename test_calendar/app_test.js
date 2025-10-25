// --- 유틸 ---
const $ = (sel, el=document) => el.querySelector(sel);
const $$ = (sel, el=document) => [...el.querySelectorAll(sel)];
const fmt = (d) => new Date(d).toLocaleDateString('ko-KR', {year:'numeric', month:'short', day:'numeric'});
const addDays = (d, n) => {
  const x = new Date(d); x.setDate(x.getDate() + n); return x.toISOString().slice(0,10);
};

// 서버 주소(동일 도메인 기준). 필요시 변경.
const API = {
  createPlan: async (payload) => {
    try {
      const r = await fetch('/api/plans', {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
      });
      if (!r.ok) throw new Error('server error');
      return await r.json();
    } catch (e) { return null; }
  },
  addObs: async (planId, payload) => {
    try {
      const r = await fetch(`/api/plans/${planId}/observations`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
      });
      if (!r.ok) throw new Error('server error');
      return await r.json();
    } catch (e) { return null; }
  }
};

// --- 로컬 Fallback: 간단 규칙 기반 일정 템플릿 ---
function localGeneratePlan({ crop, start_date, method, environment, area, variety, notes }) {
  const stages = [
    { key:'transplant', name:'정식', offset:0 },
    { key:'establish',  name:'활착/초기생육', offset:7 },
    { key:'veg',        name:'생장기', offset:21 },
    { key:'flower',     name:'개화/결실기', offset:40 },
    { key:'harvest',    name:'수확기', offset:70 }
  ];
  const envMod = (environment === 'open') ? 1 : (environment === 'hydroponic' ? 0.8 : 0.9);

  const tasks = [];
  function pushTask(stageKey, name, offset, checklist=[], notes='') {
    tasks.push({
      name, stage: stageKey, due_date: addDays(start_date, Math.round(offset*envMod)),
      checklist, notes
    });
  }

  // 핵심 작업(예시 규칙)
  pushTask('transplant','정식 준비/점검', -2, ['토양/배지 수분', '관수라인/EC/PH', '정식 도구 소독']);
  pushTask('transplant', method==='seed' ? '파종' : '정식', 0, ['식재밀도 준수','묘 활력 확인']);

  pushTask('establish','활착 관리', 5, ['고온/건조 시 차광','토양수분 유지','초기 병해 관찰']);
  pushTask('veg','추가 유인/적심', 24, ['주지 유인','곁순 정리']);
  pushTask('veg','추비/관주', 28, ['EC/PH 점검','질소 과다 주의']);
  pushTask('flower','개화/수분 관리', 42, ['수분 보조(필요시)','개화기 방제']);
  pushTask('flower','병해충 방제', 48, ['총채류/진딧물 예찰','끈끈이트랩 교체']);
  pushTask('harvest','예상 첫 수확', 70, ['표준 수확지표 확인','수확 후 품질 관리']);

  return {
    id: `local-${Math.random().toString(36).slice(2,8)}`,
    crop, start_date, method, environment, area, variety, notes,
    tasks, // 평면 리스트
  };
}

// --- 타임라인 렌더 ---
function renderPlan(plan) {
  const meta = $('#plan-meta');
  meta.innerHTML = `
    <span class="badge-stage">작물: ${plan.crop}</span>
    &nbsp;·&nbsp; 정식일: <strong>${fmt(plan.start_date)}</strong>
    &nbsp;·&nbsp; 방식: ${plan.method} / 환경: ${plan.environment}
    ${plan.variety ? `&nbsp;·&nbsp; 품종: ${plan.variety}` : ''}
    ${plan.area ? `&nbsp;·&nbsp; 면적: ${plan.area}ha` : ''}
  `;

  // 날짜(주차)별 그룹핑
  const byDate = {};
  for (const t of plan.tasks) {
    const key = t.due_date;
    (byDate[key] ||= []).push(t);
  }

  const container = $('#timeline');
  container.innerHTML = '';
  Object.keys(byDate).sort().forEach(date => {
    const group = document.createElement('div');
    group.className = 'time-group';
    group.innerHTML = `
      <header>
        <div><strong>${fmt(date)}</strong></div>
        <div class="muted">${byDate[date].length}개 작업</div>
      </header>
    `;

    for (const task of byDate[date]) {
      const box = document.createElement('div');
      box.className = 'task';
      box.innerHTML = `
        <h4>${task.name}</h4>
        <div class="kv"><strong>단계:</strong> ${task.stage} &nbsp;·&nbsp; <strong>예정일:</strong> ${fmt(task.due_date)}</div>
        ${task.checklist?.length ? `<ul class="specs">${task.checklist.map(i=>`<li>• ${i}</li>`).join('')}</ul>`: ''}
        ${task.notes ? `<p class="desc">${task.notes}</p>`: ''}

        <div class="obs-box">
          <form class="obs-form" data-date="${task.due_date}" data-task="${task.name}">
            <input type="text" name="symptom" placeholder="관찰 내용 (예: 잎 황화, 총채벌레)" />
            <select name="severity" title="심각도">
              <option value="1">경미</option>
              <option value="2" selected>보통</option>
              <option value="3">심각</option>
            </select>
            <input type="text" name="note" placeholder="메모 (예: 하우스 내부 습도 높음)" />
            <button class="btn-primary" type="submit">관찰 저장</button>
          </form>
          <div class="obs-feed" hidden></div>
        </div>
      `;
      group.appendChild(box);

      // 관찰 폼 핸들러
      const form = box.querySelector('form.obs-form');
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const payload = {
          date: form.dataset.date,
          task_name: form.dataset.task,
          symptom: fd.get('symptom')?.toString() || '',
          severity: Number(fd.get('severity') || 2),
          note: fd.get('note')?.toString() || ''
        };

        // 서버 우선, 실패 시 로컬 피드백
        let res = await API.addObs(plan.id, payload);
        if (!res) {
          res = { feedback: localFeedback(plan, payload) };
        }
        const feedEl = form.parentElement.querySelector('.obs-feed');
        feedEl.innerHTML = `<strong>피드백:</strong> ${res.feedback}`;
        feedEl.hidden = false;
      });
    }

    container.appendChild(group);
  });
}

// --- 로컬 피드백 규칙(간단 예시) ---
function localFeedback(plan, obs){
  const env = plan.environment;
  const s = (obs.symptom||'').toLowerCase();

  // 병해충 키워드
  if (/(총채|진딧|응애|해충|벌레)/.test(s)) {
    if (env === 'greenhouse') {
      return '시설재배 해충 예찰 증가 권장: 끈끈이트랩 밀도↑, 환기/차압 유지, 생물적 방제(혹파리·온실가루이 포식자) 검토';
    }
    return '해충 피해 잔재물 제거, 주변 잡초 관리, 방충망 점검. 필요 시 등록 약제 표준 희석으로 국소 처리.';
  }
  if (/(흰가루|곰팡|잎곰팡|균핵)/.test(s)) {
    return '고습성 병 발생 징후: 야간 결로↓, 환기 주기 조정, 잎 밀식 완화. 친환경 자재(유황계, 제일인산칼리 등) 또는 등록약제 예방 살포.';
  }
  if (/(황화|엽황|잎 노랗)/.test(s)) {
    return '질소/철 결핍 여부와 EC/PH 점검 권장. 관수량·배액률 확인 후 관주 비율 재설정.';
  }
  if (obs.severity >= 3) {
    return '심각 단계: 해당 구역 격리·도구 소독·전파 차단이 우선. 표준작업절차(SOP) 따라 즉시 조치·기록.';
  }
  return '관찰 기록 저장 완료. 동태 추적을 위해 2~3일 후 재관찰 권장.';
}

// --- 폼 제출 → 계획 생성 ---
$('#plan-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const err = $('#plan-error'); err.hidden = true;
  const payload = {
    crop: $('#crop').value.trim(),
    start_date: $('#start_date').value,
    method: $('#method').value,
    environment: $('#environment').value,
    area: $('#area').value ? Number($('#area').value) : null,
    variety: $('#variety').value.trim() || null,
    notes: $('#notes').value.trim() || null
  };
  if (!payload.crop || !payload.start_date) {
    err.textContent = '작물명과 정식일을 입력해주세요.'; err.hidden = false; return;
  }

  // 서버 우선
  let plan = await API.createPlan(payload);
  if (!plan) {
    // 실패 시 로컬 생성
    plan = localGeneratePlan(payload);
  }
  renderPlan(plan);
});

// --- 사이드바 토글/네비 (간단) ---
const sidebar = document.querySelector('.sidebar');
document.getElementById('sidebar-toggle').addEventListener('click', () => {
  sidebar.classList.toggle('open');
});
document.getElementById('sidebar-menu').addEventListener('click', (e) => {
  const link = e.target.closest('a.menu-item'); if (!link) return;
  e.preventDefault();
  document.querySelectorAll('.menu-item').forEach(a => a.classList.remove('active'));
  link.classList.add('active');
  const pages = document.querySelectorAll('.page');
  pages.forEach(p => p.classList.remove('visible'));
  document.getElementById(link.dataset.target).classList.add('visible');
  sidebar.classList.remove('open');
});
