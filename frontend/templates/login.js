if (typeof API_URL === 'undefined') {
    var API_URL = typeof window !== 'undefined' && window.location.port === '8080' 
        ? '/api' 
        : 'http://localhost:8000/api';
}


document.addEventListener('DOMContentLoaded', async function() {
    
    const errorDiv = document.getElementById('error-message');   
    const notice = document.getElementById('auth-notice');      
    function showError(message) {
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            errorDiv.style.color = 'red';
            errorDiv.style.backgroundColor = '#ffe3e6'; 
            errorDiv.style.padding = '8px';
            errorDiv.style.borderRadius = '4px';
        }
    }

    function showSuccess(message) {
        if (errorDiv) { 
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            errorDiv.style.color = 'green';
            errorDiv.style.backgroundColor = '#e6ffe3'; 
            errorDiv.style.padding = '8px';
            errorDiv.style.borderRadius = '4px';
        }
    }

    // --- Блок проверки, не авторизован ли пользователь уже ---
    if (typeof AuthManager !== 'undefined' && AuthManager.isAuthenticated()) { 
        try {
            const resp = await fetch(`${API_URL}/profile`, {
                headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` }
            });
            
            if (notice) { 
                if (resp.ok) {
                    const me = await resp.json();
                    notice.innerHTML = `Вы уже вошли как <strong>${me.email}</strong>. ` +
                        `<button id="switchAccountBtn" type="button" style="margin-left:8px;">Сменить аккаунт</button>`;
                } else {
                    let errorData;
                    try {
                        errorData = await resp.json();
                        console.warn('Проверка токена: невалидный токен, ответ сервера:', errorData);
                    } catch (e) {
                        console.warn('Проверка токена: ответ не JSON при ошибке', resp.status, await resp.text());
                    }
                    notice.innerHTML = `У вас уже есть активная сессия, но токен невалиден. ` +
                        `<button id="switchAccountBtn" type="button" style="margin-left:8px;">Сменить аккаунт</button>`;
                }
                
                notice.style.display = 'block';
                
                const btn = document.getElementById('switchAccountBtn');
                if (btn) {
                    btn.addEventListener('click', () => {
                        AuthManager.removeToken();
                        window.location.reload();
                    });
                }
            } else {
                console.warn('Элемент "auth-notice" не найден на странице. Уведомление о существующей сессии не будет показано.');
            }
        } catch (error) { 
            console.error('Ошибка при проверке существующего токена или получении профиля:', error);
            
            if (notice) {
                 notice.innerHTML = `У вас была активная сессия, но возникли проблемы. ` +
                        `<button id="switchAccountBtn" type="button" style="margin-left:8px;">Сменить аккаунт</button>`;
                 notice.style.display = 'block';
                 const btn = document.getElementById('switchAccountBtn');
                 if (btn) {
                     btn.addEventListener('click', () => {
                         AuthManager.removeToken();
                         window.location.reload();
                     });
                 }
            }
        }
        // Не делаем редирект - даём возможность ввести новые данные для входа
    }
    


    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    
    if (!loginForm || !usernameInput || !passwordInput) {
        console.error('Login form elements not found:', {
            form: !!loginForm,
            username: !!usernameInput,
            password: !!passwordInput
        });
        showError('Критическая ошибка: Элементы формы входа не найдены на странице.');
        return;
    }

    
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const email = usernameInput.value.trim();
        const password = passwordInput.value;

        
        if (!email || !password) {
            showError('Пожалуйста, заполните все поля');
            return;
        }

        
        if (errorDiv) errorDiv.style.display = 'none';

        try {
            const formData = new URLSearchParams();
            formData.append('username', email); // FastAPI Users ожидает 'username'
            formData.append('password', password);
            formData.append('grant_type', 'password');
            formData.append('scope', '');

            
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/x-www-form-urlencoded' 
                },
                body: formData
            });

            let data;
            
            
            try {
                
                data = await response.json();
            } catch (jsonError) {
                const errorText = await response.text();
                console.error('Failed to parse JSON response for login:', errorText, response.status, jsonError);
                showError(`Ошибка сервера: ${response.status}. Ответ не в формате JSON.`);
                return;
            }

            
            if (response.ok && data.access_token) {
                AuthManager.setToken(data.access_token);
                showSuccess('Успешный вход! Перенаправление...');
                
                setTimeout(() => { 
                    window.location.href = '/frontend/templates/base.html'; 
                }, 800);
            } else {
                
                showError(data.detail || 'Неверный email или пароль');
            }
        } catch (error) {
            
            console.error('Login error:', error);
            if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                showError('Ошибка сети: Не удалось подключиться к серверу. Проверьте ваше интернет-соединение или адрес API.');
            } else {
                showError('Произошла непредвиденная ошибка при попытке входа. Попробуйте снова.');
            }
        }
    });
});
