document.addEventListener('DOMContentLoaded', async function() {
    // Если уже авторизован — всё равно даём возможность зарегистрировать другой аккаунт
    if (AuthManager.isAuthenticated()) {
        try {
            const resp = await fetch(`${API_URL}/profile`, {
                headers: { 'Authorization': `Bearer ${AuthManager.getToken()}` }
            });
            const notice = document.getElementById('auth-notice');
            if (notice) {
                if (resp.ok) {
                    const me = await resp.json();
                    notice.innerHTML = `Вы вошли как <strong>${me.email}</strong>. ` +
                        `Можно зарегистрировать новый аккаунт, либо ` +
                        `<button id=\"switchAccountBtn\" type=\"button\" style=\"margin-left:8px;\">Сменить аккаунт</button>`;
                } else {
                    notice.innerHTML = `У вас активная сессия. ` +
                        `<button id=\"switchAccountBtn\" type=\"button\" style=\"margin-left:8px;\">Сменить аккаунт</button>`;
                }
                notice.style.display = 'block';
                const btn = document.getElementById('switchAccountBtn');
                if (btn) btn.addEventListener('click', () => {
                    AuthManager.removeToken();
                    window.location.reload();
                });
            }
        } catch {}
        // Не делаем redirect — оставляем форму доступной
    }

    const registerForm = document.getElementById('registerForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const errorDiv = document.getElementById('error-message');

    if (!registerForm || !usernameInput || !passwordInput || !confirmPasswordInput) {
        console.error('Register form elements not found:', {
            form: !!registerForm,
            username: !!usernameInput,
            password: !!passwordInput,
            confirmPassword: !!confirmPasswordInput
        });
        return;
    }

    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const email = usernameInput.value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        if (!email || !password || !confirmPassword) {
            showError('Пожалуйста, заполните все поля');
            return;
        }
        if (password !== confirmPassword) {
            showError('Пароли не совпадают');
            return;
        }
        if (password.length < 6) {
            showError('Пароль должен содержать минимум 6 символов');
            return;
        }
        if (errorDiv) errorDiv.style.display = 'none';

        try {
            const response = await fetch(`${API_URL}/auth/register-simple`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            let data = null;
            try { data = await response.json(); } catch {}

            if (response.ok) {
                const loginFormData = new URLSearchParams();
                loginFormData.append('username', email);
                loginFormData.append('password', password);
                const loginResponse = await fetch(`${API_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: loginFormData
                });
                let loginData = null;
                try { loginData = await loginResponse.json(); } catch {}
                if (loginResponse.ok && loginData.access_token) {
                    AuthManager.setToken(loginData.access_token);
                    showSuccess('Регистрация успешна! Перенаправление...');
                    setTimeout(() => { window.location.href = '/frontend/templates/base.html'; }, 800);
                } else {
                    showError('Регистрация успешна, но вход не удался. Попробуйте войти.');
                }
            } else {
                if (response.status === 409) {
                    showError('Этот email уже зарегистрирован');
                } else if (response.status === 502) {
                    showError('Сервер временно недоступен. Проверьте, запущен ли бэкенд.');
                } else {
                    showError((data && (data.detail || data.error)) || 'Ошибка регистрации');
                }
            }
        } catch (error) {
            console.error('Register error:', error);
            showError('Ошибка соединения с сервером. Попробуйте позже.');
        }
    });
});

