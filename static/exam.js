const qs = (selector, parent = document) => parent.querySelector(selector);

ace.config.set('basePath', '/static/ace');
ace.require('ace/ext/language_tools');
document.querySelectorAll('.code-editor').forEach((element) => {
  const language = element.dataset.language;
  const editor = ace.edit(element);
  editor.session.setMode(`ace/mode/${language}`);
  editor.setTheme('ace/theme/terminal');
  editor.setOptions({
    fontSize: '14px', showPrintMargin: false, tabSize: 4, useSoftTabs: true,
    enableBasicAutocompletion: true, enableLiveAutocompletion: true,
    enableSnippets: true, highlightActiveLine: true, wrap: true
  });
  editor.session.setUseSoftTabs(true);
  element.closest('.task').editor = editor;
});

document.querySelectorAll('.tab').forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.task').forEach((item) => item.classList.add('hidden'));
    tab.classList.add('active');
    const task = qs(`#${tab.dataset.target}`);
    task.classList.remove('hidden');
    task.editor.resize();
    task.editor.focus();
  };
});

async function request(endpoint, task, button) {
  const result = qs('.result', task);
  const body = { task_id: task.dataset.id, code: task.editor.getValue() };
  if (endpoint === '/api/execute') body.input = qs('.custom-input', task).value;
  button.disabled = true;
  result.textContent = endpoint === '/api/execute' ? '[ SYSTEM ] Выполняется ваш код...' : endpoint === '/api/run' ? '[ SYSTEM ] Запускаются экзаменационные тесты...' : '[ SYSTEM ] Сохраняется...';
  try {
    const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Неизвестная ошибка');
    if (endpoint === '/api/execute') {
      result.textContent = `[ ВЫВОД ВАШЕГО КОДА ]\n${data.output || '(код не вывел символов)'}`;
    } else if (endpoint === '/api/run') {
      result.innerHTML = `<b>${data.passed}/${data.total} тестов пройдено · ${data.score} баллов</b>\n${data.efficiency}\nСходство с эталонным решением: ${data.similarity}%\n\n` + data.log.map((item) => `[${item.ok ? 'OK' : 'FAIL'}] input: ${item.input || '(пусто)'} → ${item.output || item.error || '—'}; ожидалось: ${item.expected}`).join('\n');
      qs(`.tab[data-target="task-${task.dataset.id}"] small`).textContent = `${data.score}/${task.dataset.points}`;
    } else {
      result.textContent = '[ SYSTEM ] Код сохранён. Tab создаёт отступ, а подсказки появляются при наборе.';
    }
  } catch (error) { result.textContent = `[ ERROR ] ${error.message}`; }
  finally { button.disabled = false; }
}

document.querySelectorAll('.task').forEach((task) => {
  qs('.execute', task).onclick = (event) => request('/api/execute', task, event.currentTarget);
  qs('.run', task).onclick = (event) => request('/api/run', task, event.currentTarget);
  qs('.save', task).onclick = (event) => request('/api/save', task, event.currentTarget);
});

document.addEventListener('keydown', (event) => {
  const task = qs('.task:not(.hidden)');
  if (!task) return;
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') { event.preventDefault(); qs('.save', task).click(); }
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); qs('.execute', task).click(); }
  if (event.altKey && /^[1-5]$/.test(event.key)) { event.preventDefault(); qs(`.tab[data-target="task-${event.key}"]`).click(); }
});

let seconds = Number(qs('#timer').dataset.seconds);
const timer = qs('#timer');
function tick() { const h = Math.floor(seconds / 3600), m = Math.floor((seconds % 3600) / 60), s = seconds % 60; timer.textContent = [h, m, s].map((n) => String(n).padStart(2, '0')).join(':'); if (seconds-- <= 0) location.href = '/finish'; }
tick(); setInterval(tick, 1000);
