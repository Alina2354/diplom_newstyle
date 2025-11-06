document.addEventListener('DOMContentLoaded', async function() {
    // Проверка авторизации и прав админа
    if (!AuthManager.requireAuth()) return;
    const token = AuthManager.getToken();

    try {
        const prof = await fetch(`${API_URL}/profile`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!prof.ok) {
            AuthManager.removeToken();
            window.location.href = '/frontend/templates/login.html';
            return;
        }
        const me = await prof.json();
        if (!me.is_verified && me.is_superuser === undefined) {
            
        }
        if (!me.is_superuser) {
            showError('Недостаточно прав. Страница только для администратора.');
            return;
        }
    } catch (e) {
        showError('Не удалось проверить права администратора: ' + e.message);
        return;
    }

    const form = document.getElementById('costumeForm');
    const idInput = document.getElementById('costumeId');
    const titleInput = document.getElementById('title');
    const descriptionInput = document.getElementById('description');
    const priceInput = document.getElementById('price');
    const availableInput = document.getElementById('available');
    const imageInput = document.getElementById('image');
    const resetBtn = document.getElementById('resetBtn');
    const tbody = document.getElementById('costumesBody');

    async function loadCostumes() {
        try {
            const res = await fetch(`${API_URL}/costumes`);
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const items = await res.json();
            renderTable(items);
        } catch (e) {
            showError('Ошибка загрузки костюмов: ' + e.message);
        }
    }

    function renderTable(items) {
        tbody.innerHTML = '';
        if (!items.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 6; td.style.textAlign = 'center';
            td.textContent = 'Нет костюмов';
            tr.appendChild(td); tbody.appendChild(tr);
            return;
        }
        for (const c of items) {
            const tr = document.createElement('tr');
            const imageUrl = c.image_url || '/images/logo.PNG';
            const preview = `<img src="${imageUrl}" alt="${c.title}" style="height:48px;" onerror="this.src='/images/logo.PNG'; this.onerror=null;">`;
            tr.innerHTML = `
                <td style="padding:8px; border:1px solid #ccc;">${c.id}</td>
                <td style="padding:8px; border:1px solid #ccc;">${preview}</td>
                <td style="padding:8px; border:1px solid #ccc;">${c.title}</td>
                <td style="padding:8px; border:1px solid #ccc;">${c.price}</td>
                <td style="padding:8px; border:1px solid #ccc;">${c.available ? 'Да' : 'Нет'}</td>
                <td style="padding:8px; border:1px solid #ccc;">
                    <button data-id="${c.id}" class="edit-btn">Редактировать</button>
                    <button data-id="${c.id}" class="del-btn">Удалить</button>
                </td>`;
            tbody.appendChild(tr);
        }
        tbody.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                const res = await fetch(`${API_URL}/costumes/${id}`);
                if (!res.ok) return showError('Не удалось получить костюм #' + id);
                const c = await res.json();
                idInput.value = c.id;
                titleInput.value = c.title || '';
                descriptionInput.value = c.description || '';
                priceInput.value = c.price || 0;
                availableInput.checked = !!c.available;
                imageInput.value = '';
                showSuccess('Костюм загружен в форму для редактирования');
            });
        });
        tbody.querySelectorAll('.del-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                if (!confirm('Удалить костюм #' + id + '?')) return;
                try {
                    const res = await fetch(`${API_URL}/costumes/${id}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${AuthManager.getAuthHeader()?.replace('Bearer ','') ? AuthManager.getAuthHeader() : 'Bearer ' + AuthManager.getToken()}` }
                    });
                    if (!res.ok) {
                        const txt = await res.text();
                        return showError('Ошибка удаления: HTTP ' + res.status + ' ' + txt);
                    }
                    showSuccess('Удалено');
                    await loadCostumes();
                } catch (e) {
                    showError('Ошибка удаления: ' + e.message);
                }
            });
        });
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        try {
            const fd = new FormData();
            fd.append('title', titleInput.value.trim());
            fd.append('description', descriptionInput.value.trim());
            fd.append('price', String(priceInput.value || 0));
            fd.append('available', availableInput.checked ? 'true' : 'false');
            if (imageInput.files && imageInput.files[0]) fd.append('image', imageInput.files[0]);

            const isUpdate = !!idInput.value;
            const url = isUpdate ? `${API_URL}/costumes/${idInput.value}` : `${API_URL}/costumes`;
            const method = isUpdate ? 'PUT' : 'POST';
            const res = await fetch(url, {
                method,
                headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` },
                body: fd
            });
            const txt = await res.text();
            if (!res.ok) return showError('Ошибка сохранения: HTTP ' + res.status + ' ' + txt);
            showSuccess('Сохранено');
            idInput.value = ''; titleInput.value=''; descriptionInput.value=''; priceInput.value=''; availableInput.checked=true; imageInput.value='';
            await loadCostumes();
        } catch (e) {
            showError('Ошибка отправки формы: ' + e.message);
        }
    });

    resetBtn.addEventListener('click', function(){
        idInput.value = ''; titleInput.value=''; descriptionInput.value=''; priceInput.value=''; availableInput.checked=true; imageInput.value='';
    });

    loadCostumes();
});










