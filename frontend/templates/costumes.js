document.addEventListener('DOMContentLoaded', async function(){
    const grid = document.getElementById('costumesGrid');
    const modal = document.getElementById('bookingModal');
    const titleEl = document.getElementById('bookingCostumeTitle');
    const dateFromEl = document.getElementById('dateFrom');
    const dateToEl = document.getElementById('dateTo');
    const phoneEl = document.getElementById('bookingPhone');
    const infoEl = document.getElementById('availabilityInfo');
    const submitBtn = document.getElementById('bookSubmit');
    const cancelBtn = document.getElementById('bookCancel');
    const closeBtn = document.getElementById('bookClose');
    const bookingForm = document.getElementById('costumeBookingForm');
    const bookingMessage = document.getElementById('bookingMessage');

    const adminPanel = document.getElementById('adminPanel');

    // Admin controls
    const form = document.getElementById('adminCostumeForm');
    const idInput = document.getElementById('costumeId');
    const titleInput = document.getElementById('title');
    const descriptionInput = document.getElementById('description');
    const priceInput = document.getElementById('price');
    const availableInput = document.getElementById('available');
    const imageInput = document.getElementById('image');
    const resetBtn = document.getElementById('resetBtn');
    const adminCostumesBody = document.getElementById('adminCostumesBody');
    const adminReservationsBody = document.getElementById('adminReservationsBody');

    let currentCostume = null;
    let isAdmin = false;
    let items = []; // Список костюмов для доступа в других функциях

    // Check admin
    try {
        if (AuthManager.isAuthenticated()) {
            const prof = await fetch(`${API_URL}/profile`, { headers:{ 'Authorization': `Bearer ${AuthManager.getToken()}` }});
            if (prof.ok) {
                const me = await prof.json();
                isAdmin = !!me.is_superuser;
                if (isAdmin) adminPanel.style.display = 'block';
            }
        }
    } catch {}

    async function loadCostumes(){
        try{
            const res = await fetch(`${API_URL}/costumes`);
            if(!res.ok){
                const txt = await res.text();
                return showError('Ошибка загрузки костюмов: ' + txt);
            }
            items = await res.json(); // Сохраняем в переменную уровня модуля
            renderUserGrid(items);
            if (isAdmin) renderAdminTable(items);
        }catch(e){
            showError('Ошибка сети при загрузке костюмов: ' + e.message);
        }
    }

    function renderUserGrid(items){
        grid.innerHTML = '';
        if(!items.length){
            const p = document.createElement('p');
            p.textContent = 'Костюмы пока отсутствуют';
            grid.appendChild(p);
            return;
        }
        items.forEach(c => {
            const card = document.createElement('div');
            card.className = 'costume-card';
            const imageUrl = c.image_url || '/images/logo.PNG'; // Fallback на логотип, если изображение отсутствует
            card.innerHTML = `
                <img src="${imageUrl}" alt="${c.title}" onerror="this.src='/images/logo.PNG'; this.onerror=null;">
                <div class="card-content">
                    <h3>${c.title}</h3>
                    <p>${c.description ?? ''}</p>
                    <div class="card-details">
                        <span><i class="fas fa-ruble-sign"></i> Цена: ${c.price} ₽/день</span>
                    </div>
                    <button class="rent-button" data-id="${c.id}" ${!c.available?'disabled':''}>${c.available?'Заказать':'Недоступен'}</button>
                </div>`;
            grid.appendChild(card);
        });
        grid.querySelectorAll('button.rent-button').forEach(btn => {
            btn.addEventListener('click', () => openModal(parseInt(btn.dataset.id,10)));
        });
    }

    function renderAdminTable(items){
        adminCostumesBody.innerHTML = '';
        if (!items.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 6; td.style.textAlign = 'center';
            td.textContent = 'Нет костюмов';
            tr.appendChild(td); adminCostumesBody.appendChild(tr);
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
            adminCostumesBody.appendChild(tr);
        }
        adminCostumesBody.querySelectorAll('.edit-btn').forEach(btn => {
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
                window.scrollTo({ top: form.offsetTop - 20, behavior: 'smooth' });
            });
        });
        adminCostumesBody.querySelectorAll('.del-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                if (!confirm('Удалить костюм #' + id + '?')) return;
                try {
                    const res = await fetch(`${API_URL}/costumes/${id}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` }
                    });
                    const txt = await res.text();
                    if (!res.ok) return showError('Ошибка удаления: HTTP ' + res.status + ' ' + txt);
                    showSuccess('Удалено');
                    await loadCostumes();
                } catch (e) {
                    showError('Ошибка удаления: ' + e.message);
                }
            });
        });
    }

    if (form) {
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
    }

    async function loadAdminReservations(){
        if (!isAdmin) return;
        try{
            const res = await fetch(`${API_URL}/reservations/all`, { headers:{ 'Authorization': `Bearer ${AuthManager.getToken()}` } });
            const txt = await res.text();
            if (!res.ok) return showError('Ошибка загрузки броней: HTTP ' + res.status + ' ' + txt);
            const items = JSON.parse(txt);
            renderAdminReservations(items);
        }catch(e){
            showError('Ошибка загрузки броней: ' + e.message);
        }
    }

    function renderAdminReservations(items){
        adminReservationsBody.innerHTML='';
        if (!items || !items.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 6; td.style.textAlign = 'center';
            td.textContent = 'Бронирований нет';
            tr.appendChild(td); adminReservationsBody.appendChild(tr);
            return;
        }
        for (const r of items){
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding:8px; border:1px solid #ccc;">${r.id}</td>
                <td style="padding:8px; border:1px solid #ccc;">${r.user_email}</td>
                <td style="padding:8px; border:1px solid #ccc;">${r.costume_title} (#${r.costume_id})</td>
                <td style="padding:8px; border:1px solid #ccc;">${r.date_from}</td>
                <td style="padding:8px; border:1px solid #ccc;">${r.date_to}</td>
                <td style="padding:8px; border:1px solid #ccc;"><button class="res-del" data-id="${r.id}">Удалить</button></td>`;
            adminReservationsBody.appendChild(tr);
        }
        adminReservationsBody.querySelectorAll('.res-del').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                if (!confirm('Удалить бронь #' + id + '?')) return;
                try{
                    const res = await fetch(`${API_URL}/reservations/${id}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` }
                    });
                    const txt = await res.text();
                    if (!res.ok) return showError('Ошибка удаления брони: HTTP ' + res.status + ' ' + txt);
                    showSuccess('Бронь удалена');
                    loadAdminReservations();
                }catch(e){
                    showError('Ошибка удаления брони: ' + e.message);
                }
            });
        });
    }

    function openModal(costumeId){
        currentCostume = costumeId;
        const today = new Date();
        const iso = (d)=> d.toISOString().slice(0,10);
        dateFromEl.value = iso(today);
        const tomorrow = new Date(today.getTime()+24*60*60*1000);
        dateToEl.value = iso(tomorrow);
        
        // Получаем название костюма
        const costume = items.find(c => c.id === costumeId);
        if (costume) {
            titleEl.textContent = costume.title;
        } else {
            titleEl.textContent = 'Костюм #' + costumeId;
        }
        
        phoneEl.value = '';
        infoEl.textContent = '';
        infoEl.style.display = 'none';
        bookingMessage.style.display = 'none';
        modal.style.display = 'flex';
        checkAvailability();
    }

    async function checkAvailability(){
        if(!currentCostume) return;
        const from = dateFromEl.value;
        const to = dateToEl.value;
        if(!from || !to) {
            infoEl.style.display = 'none';
            return;
        }
        
        if(new Date(to) < new Date(from)){
            infoEl.style.display = 'block';
            infoEl.style.background = '#ffc107';
            infoEl.style.color = '#000';
            infoEl.textContent = 'Дата окончания не может быть раньше даты начала.';
            submitBtn.disabled = true;
            return;
        }
        
        try{
            const res = await fetch(`${API_URL}/costumes/${currentCostume}/availability?from_date=${from}&to_date=${to}`);
            if(!res.ok){
                const txt = await res.text();
                infoEl.style.display = 'block';
                infoEl.style.background = '#dc3545';
                infoEl.style.color = '#fff';
                infoEl.textContent = 'Ошибка проверки доступности: ' + txt;
                submitBtn.disabled = true;
                return;
            }
            const reservations = await res.json();
            if(reservations.length){
                infoEl.style.display = 'block';
                infoEl.style.background = '#dc3545';
                infoEl.style.color = '#fff';
                infoEl.textContent = 'На выбранные даты уже есть бронирование. Выберите другие даты.';
                submitBtn.disabled = true;
            } else {
                infoEl.style.display = 'block';
                infoEl.style.background = '#d4edda';
                infoEl.style.color = '#155724';
                infoEl.textContent = 'Даты доступны. Можно бронировать.';
                submitBtn.disabled = false;
            }
        }catch(e){
            infoEl.style.display = 'block';
            infoEl.style.background = '#dc3545';
            infoEl.style.color = '#fff';
            infoEl.textContent = 'Сетевая ошибка: ' + e.message;
            submitBtn.disabled = true;
        }
    }

    dateFromEl.addEventListener('change', checkAvailability);
    dateToEl.addEventListener('change', checkAvailability);

    function closeModal(){
        modal.style.display = 'none';
        currentCostume = null;
        bookingForm.reset();
        bookingMessage.style.display = 'none';
        infoEl.style.display = 'none';
    }

    cancelBtn.addEventListener('click', closeModal);
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    bookingForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if(!AuthManager.isAuthenticated()){
            window.location.href = '/frontend/templates/login.html';
            return;
        }
        
        const from = dateFromEl.value;
        const to = dateToEl.value;
        const phone = phoneEl.value.trim();
        
        if(!from || !to){
            bookingMessage.textContent = 'Выберите даты бронирования';
            bookingMessage.style.display = 'block';
            bookingMessage.style.background = '#dc3545';
            bookingMessage.style.color = '#fff';
            return;
        }
        
        if(!phone){
            bookingMessage.textContent = 'Укажите номер телефона';
            bookingMessage.style.display = 'block';
            bookingMessage.style.background = '#dc3545';
            bookingMessage.style.color = '#fff';
            return;
        }
        
        if(new Date(to) < new Date(from)){
            bookingMessage.textContent = 'Дата окончания не может быть раньше даты начала';
            bookingMessage.style.display = 'block';
            bookingMessage.style.background = '#dc3545';
            bookingMessage.style.color = '#fff';
            return;
        }
        
        try{
            // Проверка доступности
            const availabilityRes = await fetch(`${API_URL}/costumes/${currentCostume}/availability?from_date=${from}&to_date=${to}`);
            if(!availabilityRes.ok){
                // Если проверка доступности не удалась, все равно пытаемся создать заказ
                // (бэкенд проверит конфликты еще раз)
                console.warn('Проверка доступности не удалась, но продолжаем создание заказа');
            } else {
                const conflicts = await availabilityRes.json();
                if(conflicts && conflicts.length > 0){
                    bookingMessage.textContent = 'На выбранные даты уже есть бронирование. Выберите другие даты.';
                    bookingMessage.style.display = 'block';
                    bookingMessage.style.background = '#dc3545';
                    bookingMessage.style.color = '#fff';
                    return;
                }
            }
            
            // Получаем название костюма
            const costume = items.find(c => c.id === currentCostume);
            const costumeTitle = costume ? costume.title : `Костюм #${currentCostume}`;
            
            // Создаем заказ
            const title = `Бронирование костюма: ${costumeTitle}`;
            const orderData = {
                title: title,
                status: 'новая',
                phone: phone,
                costume_id: currentCostume,
                date_from: from,
                date_to: to
            };
            
            const token = AuthManager.getToken();
            const res = await fetch(`${API_URL}/orders`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(orderData)
            });
            
            if(!res.ok){
                let errorText = '';
                try {
                    const errorData = await res.json();
                    errorText = errorData.detail || errorData.message || 'Неизвестная ошибка';
                } catch (e) {
                    errorText = await res.text();
                }
                
                // Специальная обработка для конфликтов (409)
                if (res.status === 409) {
                    bookingMessage.textContent = '❌ ' + (errorText || 'Выбранные даты уже заняты. Пожалуйста, выберите другие даты.');
                } else {
                    bookingMessage.textContent = 'Ошибка создания заявки: ' + errorText;
                }
                bookingMessage.style.display = 'block';
                bookingMessage.style.background = '#dc3545';
                bookingMessage.style.color = '#fff';
                return;
            }
            
            bookingMessage.textContent = 'Заявка на бронирование успешно отправлена! Мы свяжемся с вами для подтверждения.';
            bookingMessage.style.display = 'block';
            bookingMessage.style.background = '#28a745';
            bookingMessage.style.color = '#fff';
            
            // Обновляем список заказов, если открыт личный кабинет
            if (typeof window.refreshOrdersIfDashboard === 'function') {
                window.refreshOrdersIfDashboard();
            }
            
            setTimeout(() => {
                closeModal();
                // Перезагружаем костюмы для обновления доступности
                loadCostumes();
            }, 2000);
            
        }catch(e){
            bookingMessage.textContent = 'Сетевая ошибка: ' + e.message;
            bookingMessage.style.display = 'block';
            bookingMessage.style.background = '#dc3545';
            bookingMessage.style.color = '#fff';
        }
    });

    await loadCostumes();
    await loadAdminReservations();
});
