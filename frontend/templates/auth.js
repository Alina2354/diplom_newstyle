var API_URL = typeof window !== 'undefined' && window.location.port === '8080' 
    ? '/api'  // Используем прокси если фронтенд на порту 8080
    : 'http://localhost:8000/api';  // Прямой URL к бэкенду

class AuthManager {
    static getToken() {
        return localStorage.getItem('jwt_token');
    }

    static setToken(token) {
        localStorage.setItem('jwt_token', token);
    }

    static removeToken() {
        localStorage.removeItem('jwt_token');
    }

    static isAuthenticated() {
        return !!this.getToken();
    }

    static getAuthHeader() {
        const token = this.getToken();
        return token ? `Bearer ${token}` : null;
    }

    static requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/frontend/templates/login.html';
            return false;  
        }
        return true; 
    }

    // Редирект если уже авторизован (для страниц логина/регистрации)
    // Используется чтобы не показывать форму входа уже авторизованным пользователям
    static redirectIfAuthenticated() {
        if (this.isAuthenticated()) {
            window.location.href = '/frontend/templates/base.html';
            return true;
        }
        return false;
    }
}


function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        
        errorDiv.style.background = '#dc3545';  
        errorDiv.style.color = 'white';          
        errorDiv.style.padding = '10px';         
        errorDiv.style.borderRadius = '5px';    
        errorDiv.style.marginTop = '10px';       
    } else {
        alert(message);
    }
}


function showSuccess(message) {
    
    const successDiv = document.getElementById('success-message');
    
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.style.display = 'block';
        successDiv.style.background = '#28a745';
        successDiv.style.color = 'white';
        successDiv.style.padding = '10px';
        successDiv.style.borderRadius = '5px';
        successDiv.style.marginTop = '10px';
    } else {
        
        alert(message);
    }
}

// Функция-обертка для запросов к API

async function apiRequest(url, options = {}) {

    try {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Ошибка запроса');
        }
        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}
