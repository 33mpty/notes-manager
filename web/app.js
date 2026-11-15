const get = (id) => document.getElementById(id);
const form = get('form');
const list = get('notes');
const status = get('status');
let editing = null;
let labels = ['Без метки'];

async function api(path, options) {
  const response = await fetch(path, options);
  if (response.status === 204) return;
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw Error(problem.error || 'Ошибка запроса: ' + response.status);
  }
  return response.json();
}

function setLabels(selected = 'Без метки') {
  get('label').replaceChildren();
  for (const label of new Set([...labels, selected])) {
    get('label').add(new Option(label, label, false, label === selected));
  }
}

function resetForm() {
  form.reset();
  setLabels();
  editing = null;
  get('form-title').textContent = 'Новая заметка';
  get('cancel').hidden = true;
}

function node(tag, text) {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
}

async function loadNotes() {
  const notes = await api('/api/notes');
  list.replaceChildren();
  if (!notes.length) list.append(node('p', 'Список пока пуст.'));
  for (const note of notes) {
    const card = document.createElement('article');
    const edit = node('button', 'Изменить');
    edit.onclick = () => {
      editing = note.id;
      get('title').value = note.title;
      get('body').value = note.body;
      setLabels(note.label);
      get('form-title').textContent = 'Редактирование заметки';
      get('cancel').hidden = false;
      get('title').focus();
    };
    const remove = node('button', 'Удалить');
    remove.onclick = async () => {
      if (!confirm('Удалить заметку?')) return;
      try {
        await api('/api/notes/' + note.id, { method: 'DELETE' });
        if (editing === note.id) resetForm();
        await loadNotes();
      } catch (error) {
        status.textContent = error.message;
      }
    };
    card.append(node('small', note.label), node('h3', note.title), node('p', note.body), edit, remove);
    list.append(card);
  }
}

form.onsubmit = async (event) => {
  event.preventDefault();
  get('save').disabled = true;
  status.textContent = '';
  try {
    await api(editing === null ? '/api/notes' : '/api/notes/' + editing, {
      method: editing === null ? 'POST' : 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: get('title').value, body: get('body').value, label: get('label').value })
    });
    resetForm();
    await loadNotes();
  } catch (error) {
    status.textContent = error.message;
  } finally {
    get('save').disabled = false;
  }
};

get('cancel').onclick = resetForm;
api('/api/labels').then((data) => {
  labels = data;
  setLabels(get('label').value);
}).catch(() => { status.textContent = 'Справочник недоступен. Можно использовать метку «Без метки».'; });
loadNotes().catch((error) => { status.textContent = error.message; });
