document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('add-bookmark-form');
    const bookmarksList = document.getElementById('bookmarks-list');

    // Функция для загрузки закладок
    const loadBookmarks = () => {
        fetch('/bookmarks')
            .then(response => response.json())
            .then(bookmarks => {
                bookmarksList.innerHTML = ''; // Очищаем список
                if (bookmarks.length === 0) {
                    bookmarksList.innerHTML = '<li>Пока нет ни одной закладки.</li>';
                    return;
                }
                bookmarks.forEach(bookmark => {
                    const li = document.createElement('li');
                    li.innerHTML = `<a href="${bookmark.url}" target="_blank">[${bookmark.id}] ${bookmark.title}</a>`;
                    bookmarksList.appendChild(li);
                });
            })
            .catch(error => {
                console.error('Ошибка при загрузке закладок:', error);
                bookmarksList.innerHTML = '<li>Ошибка при загрузке закладок.</li>';
            });
    };

    // Обработчик отправки формы
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const titleInput = document.getElementById('title');
        const urlInput = document.getElementById('url');

        fetch('/bookmarks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: titleInput.value, url: urlInput.value }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(() => {
            titleInput.value = ''; // Очищаем поля
            urlInput.value = '';
            loadBookmarks(); // Перезагружаем список
        })
        .catch(error => console.error('Ошибка при добавлении закладки:', error));
    });

    // Начальная загрузка
    loadBookmarks();
});
