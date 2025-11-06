window.refreshOrdersIfDashboard = function() {
    
    if (typeof loadUserOrders === 'function') {
        console.log('Обновление списка заказов в личном кабинете...');
        setTimeout(() => {
            loadUserOrders();
        }, 500);
    } else if (window.location.pathname.includes('dashboard')) {
        
        console.log('Перезагрузка страницы личного кабинета для обновления заказов...');
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
};

// Функция для отправки заказа на сервер
async function submitOrder(formData, orderType) {
    console.log('submitOrder вызвана:', { formData, orderType });
    
    if (typeof AuthManager === 'undefined') {
        console.error('AuthManager не определен! Проверьте подключение auth.js');
        throw new Error('AuthManager не загружен. Перезагрузите страницу.');
    }
    
    const token = AuthManager.getToken();
    
    if (!token) {
        console.error('Токен авторизации отсутствует');
        throw new Error('Необходима авторизация. Пожалуйста, войдите в систему.');
    }
    
    
    const title = `${orderType}: ${formData.material || 'Материал не указан'}${formData.comment ? ' - ' + formData.comment.substring(0, 50) : ''}`;
    
    const requestBody = {
        title: title,
        status: 'новая',
        phone: formData.phone || null
    };
    
    console.log('Отправка запроса на создание заказа:', { url: `${API_URL}/orders`, body: requestBody });
    
    try {
        const response = await fetch(`${API_URL}/orders`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Ответ сервера:', { status: response.status, statusText: response.statusText });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Ошибка создания заказа:', errorText);
            throw new Error(`Ошибка создания заказа: ${response.status} ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Заказ успешно создан:', result);
        return result;
    } catch (error) {
        console.error('Ошибка сети при создании заказа:', error);
        throw error;
    }
}

// Функция для получения данных из формы по ID префиксу
function getFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return null;
    
    const prefix = formId.replace('sewOrderForm', '');
    const orderType = form.getAttribute('data-order-type') || 'Заказ';
    
    return {
        date: document.getElementById(`sewDate${prefix}`)?.value || '',
        phone: document.getElementById(`phoneNumber${prefix}`)?.value || '',
        material: document.getElementById(`sewMaterial${prefix}`)?.value || '',
        comment: document.getElementById(`sewComment${prefix}`)?.value || '',
        orderType: orderType,
        formId: formId,
        messageBoxId: `sewOrderMessage${prefix}`,
        modalId: `sewOrderModal${prefix}`
    };
}

// Флаг для предотвращения повторной отправки
const submittingForms = new Set();

// Универсальный обработчик для всех форм заказов
async function handleOrderFormSubmit(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const form = e.target;
    const formId = form.id;
    console.log('Обработка отправки формы:', formId);
    
    // Проверяем, не отправляется ли уже эта форма
    if (submittingForms.has(formId)) {
        console.log('Форма уже отправляется, игнорируем повторную отправку:', formId);
        return;
    }
    
    if (!formId.startsWith('sewOrderForm')) {
        console.warn('Форма не распознана как форма заказа:', formId);
        return;
    }
    
    const formData = getFormData(formId);
    if (!formData) {
        console.error('Не удалось получить данные формы:', formId);
        return;
    }
    
    // Отмечаем форму как отправляемую
    submittingForms.add(formId);
    
    const messageBox = document.getElementById(formData.messageBoxId);
    
    // Проверяем авторизацию
    if (typeof AuthManager === 'undefined' || !AuthManager.isAuthenticated()) {
        submittingForms.delete(formId); // Освобождаем флаг
        const shouldRedirect = confirm('Для создания заказа необходимо войти в систему. Перейти на страницу входа?');
        if (shouldRedirect) {
            window.location.href = '/frontend/templates/login.html';
        }
        return;
    }
    

    if (messageBox) {
        messageBox.textContent = 'Отправка заявки...';
        messageBox.style.display = 'block';
        messageBox.style.background = '#ffc107';
        messageBox.style.color = '#000';
    }
    
    try {
        const orderData = {
            date: formData.date,
            phone: formData.phone,
            material: formData.material,
            comment: formData.comment
        };
        
        const createdOrder = await submitOrder(orderData, formData.orderType);
        
        
        if (messageBox) {
            messageBox.textContent = 'Заявка успешно отправлена! Мы свяжемся с вами для подтверждения.';
            messageBox.style.display = 'block';
            messageBox.style.background = '#28a745';
            messageBox.style.color = '#fff';
        }
        
        // Обновляем список заказов, если открыт личный кабинет
        if (typeof window.refreshOrdersIfDashboard === 'function') {
            window.refreshOrdersIfDashboard();
        }
        
        
        setTimeout(() => {
            form.reset();
            submittingForms.delete(formId); // Освобождаем флаг после успешной отправки
            const modal = document.getElementById(formData.modalId);
            if (modal) modal.style.display = 'none';
            if (messageBox) messageBox.style.display = 'none';
        }, 1500);
        
    } catch (error) {
        submittingForms.delete(formId); // Освобождаем флаг при ошибке
        console.error('Ошибка отправки заказа:', error);
        if (messageBox) {
            messageBox.textContent = 'Ошибка: ' + error.message;
            messageBox.style.display = 'block';
            messageBox.style.background = '#dc3545';
            messageBox.style.color = '#fff';
        }
    }
}

// Флаг для отслеживания инициализации
let orderFormsInitialized = false;
let globalSubmitHandlerAttached = false;

// Функция для инициализации обработчиков форм заказов
function initOrderForms() {
    // Предотвращаем повторную инициализацию
    if (orderFormsInitialized) {
        console.log('Формы заказов уже инициализированы, пропускаем');
        return;
    }
    
    console.log('Инициализация обработчиков форм заказов...');
    
    // Добавляем глобальный обработчик только один раз
    if (!globalSubmitHandlerAttached) {
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form && form.id && form.id.startsWith('sewOrderForm')) {
                console.log('Перехвачена отправка формы заказа:', form.id);
                handleOrderFormSubmit(e);
            }
        }, true);
        globalSubmitHandlerAttached = true;
        console.log('Глобальный обработчик submit установлен');
    }
    
    const formIds = ['sewOrderForm0', 'sewOrderForm1', 'sewOrderForm2', 'sewOrderForm3'];
    
    formIds.forEach(formId => {
        const form = document.getElementById(formId);
        if (form) {
            // Проверяем, не добавлен ли уже обработчик
            if (form.hasAttribute('data-order-handler-attached')) {
                console.log(`Форма ${formId} уже имеет обработчик, пропускаем`);
                return;
            }
            
            console.log(`Форма ${formId} найдена, устанавливаем обработчик`);
            form.setAttribute('data-order-handler-attached', 'true');
            form.addEventListener('submit', handleOrderFormSubmit);
        } else {
            console.log(`Форма ${formId} не найдена`);
        }
    });
    
    orderFormsInitialized = true;
    console.log('Инициализация форм заказов завершена');
}


console.log('order-forms.js загружен, состояние DOM:', document.readyState);


function doInit() {
    console.log('Выполнение инициализации форм...');
    initOrderForms();
    
    // Дополнительная проверка для форм, которые могли появиться позже (только один раз)
    if (!orderFormsInitialized) {
        setTimeout(() => {
            console.log('Дополнительная проверка форм...');
            const formIds = ['sewOrderForm0', 'sewOrderForm1', 'sewOrderForm2', 'sewOrderForm3'];
            formIds.forEach(formId => {
                const form = document.getElementById(formId);
                if (form && !form.hasAttribute('data-order-handler-attached')) {
                    console.log(`Добавляем обработчик к ${formId}`);
                    form.setAttribute('data-order-handler-attached', 'true');
                    form.addEventListener('submit', handleOrderFormSubmit);
                }
            });
        }, 1000);
    }
}

// Инициализация только один раз
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', doInit);
} else {
    doInit();
}
