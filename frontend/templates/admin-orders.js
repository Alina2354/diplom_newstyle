document.addEventListener('DOMContentLoaded', async function(){
    if (!AuthManager.requireAuth()) return;
    const token = AuthManager.getToken();

    // Проверка прав админа
    try {
        const prof = await fetch(`${API_URL}/profile`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!prof.ok) {
            AuthManager.removeToken();
            window.location.href = '/frontend/templates/login.html';
            return;
        }
        const me = await prof.json();
        if (!me.is_superuser) {
            showError('Недостаточно прав. Страница только для администратора.');
            return;
        }
    } catch (e) {
        showError('Не удалось проверить права администратора: ' + e.message);
        return;
    }

    const tbody = document.getElementById('ordersBody');
    const statusFilter = document.getElementById('statusFilter');
    const reloadBtn = document.getElementById('reloadBtn');

    reloadBtn.addEventListener('click', loadOrders);
    statusFilter.addEventListener('change', loadOrders);

    async function loadOrders(){
        try {
            const res = await fetch(`${API_URL}/orders/all`, { headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` } });
            const txt = await res.text();
            if (!res.ok) return showError('Ошибка загрузки заказов: HTTP ' + res.status + ' ' + txt);
            const items = JSON.parse(txt);
            render(items);
        } catch (e) {
            showError('Ошибка загрузки заказов: ' + e.message);
        }
    }

    function render(items){
        tbody.innerHTML = '';
        const f = statusFilter.value;
        const filtered = f ? items.filter(x => x.status === f) : items;
        if (!filtered.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 8; td.style.textAlign = 'center';
            td.textContent = 'Нет заказов';
            tr.appendChild(td); tbody.appendChild(tr);
            return;
        }
        for (const o of filtered) {
            const tr = document.createElement('tr');
            const dateStr = o.created_at ? new Date(o.created_at).toLocaleString() : '';
            const costumeTitle = o.costume_title || (o.costume_id ? ('#' + o.costume_id) : '—');
            const phone = o.phone || '—';
            
            // Формируем название заказа с датами бронирования, если есть
            let titleText = o.title;
            if (o.costume_id && o.date_from && o.date_to) {
                const fromDate = new Date(o.date_from);
                const toDate = new Date(o.date_to);
                const fromStr = `${fromDate.getDate().toString().padStart(2,'0')}.${(fromDate.getMonth()+1).toString().padStart(2,'0')}.${fromDate.getFullYear()}`;
                const toStr = `${toDate.getDate().toString().padStart(2,'0')}.${(toDate.getMonth()+1).toString().padStart(2,'0')}.${toDate.getFullYear()}`;
                titleText += ` (${fromStr} - ${toStr})`;
            }
            
            tr.innerHTML = `
                <td style="padding:8px; border:1px solid #ccc;">${o.id}</td>
                <td style="padding:8px; border:1px solid #ccc;">${o.user_email}</td>
                <td style="padding:8px; border:1px solid #ccc;">${titleText}</td>
                <td style="padding:8px; border:1px solid #ccc;">${phone}</td>
                <td style="padding:8px; border:1px solid #ccc;">${costumeTitle}</td>
                <td style="padding:8px; border:1px solid #ccc;">${dateStr}</td>
                <td style="padding:8px; border:1px solid #ccc;">${o.status}</td>
                <td style="padding:8px; border:1px solid #ccc;">
                    <select data-id="${o.id}" class="status-select">
                        <option ${o.status==='новая'?'selected':''} value="новая">новая</option>
                        <option ${o.status==='в обработке'?'selected':''} value="в обработке">в обработке</option>
                        <option ${o.status==='завершена'?'selected':''} value="завершена">завершена</option>
                    </select>
                    <button data-id="${o.id}" class="apply-btn">Применить</button>
                </td>`;
            tbody.appendChild(tr);
        }
        tbody.querySelectorAll('.apply-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                const select = tbody.querySelector(`select.status-select[data-id="${id}"]`);
                try {
                    const res = await fetch(`${API_URL}/orders/${id}/status`, {
                        method:'PATCH',
                        headers:{ 'Content-Type':'application/json', 'Authorization': `Bearer ${AuthManager.getToken()}` },
                        body: JSON.stringify({ status: select.value })
                    });
                    const txt = await res.text();
                    if (!res.ok) return showError('Ошибка обновления статуса: HTTP ' + res.status + ' ' + txt);
                    showSuccess('Статус обновлён');
                    loadOrders();
                } catch (e) {
                    showError('Ошибка обновления статуса: ' + e.message);
                }
            });
        });
    }

    loadOrders();
});










