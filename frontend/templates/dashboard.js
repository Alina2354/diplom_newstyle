document.addEventListener('DOMContentLoaded', function() {
    if (!AuthManager.requireAuth()) {
        return;  
    }

    loadUserProfile();  
    loadUserOrders();    
    setupLogout();    
    setupProfileForm();  
});


async function loadUserProfile() {
    try {
        
        const token = AuthManager.getToken();
        
        
        const response = await fetch(`${API_URL}/profile`, {
            method: 'GET',  
            headers: {     
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        
        if (!response.ok) {
            
            let errorText = '';
            
            
            const contentType = response.headers.get('content-type');
            
            
            if (contentType && contentType.includes('application/json')) {
                try {
                    
                    const errorData = await response.json();
                    errorText = errorData.detail || errorData.message || 'Неизвестная ошибка';
                } catch (e) {
                    errorText = await response.text();
                }
            } else {
                errorText = await response.text();
            }
            
            console.error(`Ошибка профиля HTTP ${response.status}:`, errorText);
            showError('Ошибка загрузки профиля (HTTP '+response.status+'): ' + (errorText || response.statusText));

            if (response.status === 401) {
                
                AuthManager.removeToken();
                window.location.href = '/frontend/templates/login.html';
            }
            return;  
        }
        
        
        const userData = await response.json();
        
        
        displayUserInfo(userData);
        
    } catch (error) {
        
        console.error('Network Error loading profile:', error);
        showError('Сетевая ошибка при загрузке профиля: ' + error.message);
    }
}

// Асинхронная функция для загрузки заявок пользователя
// Логика аналогична loadUserProfile()
async function loadUserOrders() {
    try {
        const token = AuthManager.getToken();
        const response = await fetch(`${API_URL}/orders/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            let errorText = '';
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                try {
                    const errorData = await response.json();
                    errorText = errorData.detail || errorData.message || 'Неизвестная ошибка';
                } catch (e) {
                    errorText = await response.text();
                }
            } else {
                errorText = await response.text();
            }
            console.error(`Ошибка загрузки заявок HTTP ${response.status}:`, errorText);
            showError('Ошибка загрузки заявок (HTTP '+response.status+'): ' + (errorText || response.statusText));
            if (response.status === 401) {
                AuthManager.removeToken();
                window.location.href = '/frontend/templates/login.html';
            }
            return;
        }
        
        
        const orders = await response.json();
        if (!Array.isArray(orders)) {
            console.error('Ожидался массив заказов, получено:', orders);
            showError('Некорректный формат данных заказов');
            renderOrdersTable([]); 
            return;
        }
        
        
        renderOrdersTable(orders);
        
    } catch (error) {
        console.error('Network Error loading orders:', error);
        showError('Сетевая ошибка при загрузке заявок: ' + error.message);
        renderOrdersTable([]);
    }
}

// Функция для отрисовки таблицы заявок в HTML

function renderOrdersTable(orders) {
    const tbody = document.getElementById('user-orders-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!orders.length) {
        const row = document.createElement('tr');     
        const cell = document.createElement('td');     
        cell.colSpan = 4;
        cell.style.textAlign = 'center';
        cell.textContent = 'У вас пока нет заявок.';
        row.appendChild(cell);
        tbody.appendChild(row);
        return;  
    }
    
    
    for (const order of orders) {
        const row = document.createElement('tr');
        const titleCell = document.createElement('td');
        
        // Если это заказ на бронирование костюма, добавляем информацию о датах
        let titleText = order.title;
        if (order.costume_id && order.date_from && order.date_to) {
            const fromDate = new Date(order.date_from);
            const toDate = new Date(order.date_to);
            const fromStr = `${fromDate.getDate().toString().padStart(2,'0')}.${(fromDate.getMonth()+1).toString().padStart(2,'0')}.${fromDate.getFullYear()}`;
            const toStr = `${toDate.getDate().toString().padStart(2,'0')}.${(toDate.getMonth()+1).toString().padStart(2,'0')}.${toDate.getFullYear()}`;
            titleText += ` (${fromStr} - ${toStr})`;
        }
        titleCell.textContent = titleText;
        titleCell.style.padding = '8px';
        titleCell.style.border = '1px solid #ccc';
        
        const dateCell = document.createElement('td');
        const dt = new Date(order.created_at);
        const dateStr = `${dt.getDate().toString().padStart(2,'0')}.${(dt.getMonth()+1).toString().padStart(2,'0')}.${dt.getFullYear()} ${dt.getHours().toString().padStart(2,'0')}:${dt.getMinutes().toString().padStart(2,'0')}`;
        dateCell.textContent = dateStr;
        dateCell.style.padding = '8px';
        dateCell.style.border = '1px solid #ccc';

        const phoneCell = document.createElement('td');
        phoneCell.textContent = order.phone || '—';
        phoneCell.style.padding = '8px';
        phoneCell.style.border = '1px solid #ccc';
 
        const statusCell = document.createElement('td');
        statusCell.textContent = order.status;
        statusCell.style.padding = '8px';
        statusCell.style.border = '1px solid #ccc';


        row.appendChild(titleCell);
        row.appendChild(dateCell);
        row.appendChild(phoneCell);
        row.appendChild(statusCell);
        

        tbody.appendChild(row);
    }
}


function displayUserInfo(userData) {
    const emailDisplay = document.getElementById('user-email');
    const userIdDisplay = document.getElementById('user-id');
    const userStatusDisplay = document.getElementById('user-status');
    if (emailDisplay) {
        emailDisplay.textContent = userData.email || 'Email не указан';
    }

    if (userIdDisplay) {
        userIdDisplay.textContent = `ID: ${userData.id}`;
    }

    if (userStatusDisplay) {
        const status = userData.is_active ? 'Активен' : 'Неактивен';
        userStatusDisplay.textContent = `Статус: ${status}`;
    }

    const img = document.getElementById('profile-photo');
    if (img) {
        
        if (userData.photo_url) {
            img.src = userData.photo_url;
        } else {
            img.src = '/images/logo.PNG';
        }
    }

    
    const nameInput = document.getElementById('pf-name');
    const phoneInput = document.getElementById('pf-phone');
    const ageInput = document.getElementById('pf-age');
    
    
    if (nameInput) nameInput.value = userData.name || '';
    if (phoneInput) phoneInput.value = userData.phone || '';
    if (ageInput) ageInput.value = userData.age != null ? userData.age : '';
    displayProfileInfo(userData);
}
function displayProfileInfo(userData) {
    let profileInfoDiv = document.getElementById('profile-info-display');
    if (!profileInfoDiv) {
        profileInfoDiv = document.createElement('div');
        profileInfoDiv.id = 'profile-info-display';
        profileInfoDiv.style.cssText = 'margin-top: 16px; padding: 12px; background: rgba(255, 255, 255, 0.9); border-radius: 8px;';

        const form = document.getElementById('profileForm');

        if (form && form.parentNode) {
            form.parentNode.insertBefore(profileInfoDiv, form.nextSibling);
        }
    }
    
    
    let html = '<h4 style="margin-top: 0; color: #5a2d82;">Информация профиля:</h4>';
    
    
    if (userData.name) {
        html += `<p><strong>Имя:</strong> ${userData.name}</p>`;
    }
    
    
    if (userData.phone) {
        html += `<p><strong>Телефон:</strong> ${userData.phone}</p>`;
    }
    
    
    if (userData.age != null) {
        html += `<p><strong>Возраст:</strong> ${userData.age} лет</p>`;
    }
    
    
    if (!userData.name && !userData.phone && userData.age == null) {
        html += '<p style="color: #666; font-style: italic;">Заполните форму выше, чтобы добавить информацию о себе</p>';
    }
    
    profileInfoDiv.innerHTML = html;
}

function setupLogout() {
    
    const logoutBtn = document.getElementById('logout-btn');
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function() {
            try {
                const token = AuthManager.getToken();
                await fetch(`${API_URL}/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
            } catch (error) {
                console.error('Logout error:', error);
            } finally {
                AuthManager.removeToken();
                window.location.href = '/frontend/templates/index.html';
            }
        });
    }
}

// Функция для настройки формы профиля и всех её обработчиков
function setupProfileForm() {
    
    const form = document.getElementById('profileForm');
    const uploadBtn = document.getElementById('pf-upload-btn');
    const fileInput = document.getElementById('pf-photo');
    const errorDiv = document.getElementById('error-message');
    const successDiv = document.getElementById('success-message');
    const toggleBtn = document.getElementById('toggle-profile-form-btn');
    const toggleText = document.getElementById('toggle-form-text');
    
    if (toggleBtn && form) {
        toggleBtn.addEventListener('click', function() {
            
            const isVisible = form.style.display !== 'none';
            
            if (isVisible) {
                
                form.style.display = 'none';
                if (toggleText) toggleText.textContent = 'Изменить профиль';
            } else {
                form.style.display = 'block';
                if (toggleText) toggleText.textContent = 'Скрыть форму';
            }
        });
    }

    
    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', async function() {
            const file = fileInput.files && fileInput.files[0];
            
            if (!file) {
                showError('Выберите файл для загрузки');
                return; 
            }
            
            try {
                const token = AuthManager.getToken();
                const fd = new FormData();
                fd.append('image', file);
                const resp = await fetch(`${API_URL}/profile/photo`, {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}` 
                    },
                    body: fd  
                });
                
                const data = await resp.json();
                
                if (!resp.ok) {
                    showError(data.detail || 'Не удалось загрузить фото');
                    return;
                }
                
                
                const img = document.getElementById('profile-photo');
                if (img && data.photo_url) img.src = data.photo_url;
                
                showSuccess('Фото успешно обновлено');
                
            } catch (e) {
                console.error('Upload photo error:', e);
                showError('Ошибка загрузки фото');
            }
        });
    }

    
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const token = AuthManager.getToken();
                const nameVal = document.getElementById('pf-name').value.trim();
                const phoneVal = document.getElementById('pf-phone').value.trim();
                const ageVal = document.getElementById('pf-age').value.trim();
                
                const body = {
                    name: nameVal === '' ? null : nameVal,
                    phone: phoneVal === '' ? null : phoneVal,
                    age: ageVal === '' ? null : (isNaN(Number(ageVal)) ? null : Number(ageVal))
                };
                
                
                const resp = await fetch(`${API_URL}/profile`, {
                    method: 'PUT',  
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    
                    body: JSON.stringify(body)
                });

                let data;
                const contentType = resp.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    
                    data = await resp.json();
                } else {
                    const text = await resp.text();
                    throw new Error(text || `HTTP ${resp.status}: ${resp.statusText}`);
                }
                
                if (!resp.ok) {
                    showError(data.detail || 'Не удалось сохранить профиль');
                    return;
                }
                
                
                showSuccess('Профиль успешно сохранен');
                
                
                await loadUserProfile();
                
                if (form) {
                    form.style.display = 'none';
                    const toggleText = document.getElementById('toggle-form-text');
                    if (toggleText) toggleText.textContent = 'Изменить профиль';
                }
                
                
                setTimeout(() => {
                    const successDiv = document.getElementById('success-message');
                    const errorDiv = document.getElementById('error-message');
                    
                    if (successDiv) successDiv.style.display = 'none';
                    if (errorDiv) errorDiv.style.display = 'none';
                }, 3000); 
                
            } catch (e) {
                
                console.error('Save profile error:', e);
                showError('Ошибка сохранения профиля: ' + (e.message || 'Неизвестная ошибка'));
            }
        });
    }
}
