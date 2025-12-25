// API Configuration
const API_BASE_URL = '/api/auth';

// State
let tasks = [];
let currentTaskId = null;
let isEditMode = false;
let eventListeners = [];

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper function to make API calls
async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'include'
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            let errorMessage = 'Помилка запиту';

            try {
                const errorData = await response.json();

                // Обрабатываем разные типы ошибок
                if (errorData.detail) {
                    // Простое сообщение об ошибке
                    errorMessage = errorData.detail;
                } else if (errorData.error) {
                    // Альтернативное поле для ошибки
                    errorMessage = errorData.error;
                } else if (errorData.assigned_to) {
                    // Ошибка валидации поля assigned_to
                    errorMessage = `Помилка призначення: ${errorData.assigned_to[0]}`;
                } else if (errorData.non_field_errors) {
                    // Общие ошибки валидации
                    errorMessage = errorData.non_field_errors[0];
                } else {
                    // Собираем все ошибки валидации полей
                    const errors = Object.entries(errorData)
                        .map(([field, messages]) => {
                            if (Array.isArray(messages)) {
                                return `${field}: ${messages.join(', ')}`;
                            }
                            return `${field}: ${messages}`;
                        })
                        .join('; ');

                    if (errors) {
                        errorMessage = errors;
                    }
                }
            } catch (parseError) {
                // Если не удалось распарсить JSON
                errorMessage = `Помилка ${response.status}: ${response.statusText}`;
            }

            throw new Error(errorMessage);
        }

        return method === 'DELETE' ? null : await response.json();
    } catch (error) {
        // Если это наша ошибка с сообщением, пробрасываем её дальше
        if (error.message) {
            throw error;
        }

        // Ошибки сети или другие непредвиденные ошибки
        // console.error('API Error:', error);
        throw new Error('Помилка з\'єднання з сервером');
    }
}

// Load Users
async function loadUsers() {
    try {
        const users = await apiCall(`${API_BASE_URL}/users/`);
        populateUserSelect(users);
    } catch (error) {
        console.error('Error loading users:', error);
        showNotification(window.TRANSLATIONS.error_loading_users, 'error');
    }
}

// Populate User Select
function populateUserSelect(users) {
    const select = document.getElementById('taskAssignedTo');
    if (!select) {
        console.error('taskAssignedTo select not found');
        return;
    }

    select.innerHTML = `<option value="">${window.TRANSLATIONS.not_assigned}</option>`;

    users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        option.textContent = user.get_full_name;
        select.appendChild(option);
    });
}

let currentFilter = {
    assigned_to: null
};

// Load Tasks with Filter
async function loadTasks(filters = {}) {
    try {
        let url = `${API_BASE_URL}/tasks/`;
        const params = new URLSearchParams();

        if (filters.assigned_to) {
            params.append('assigned_to', filters.assigned_to);
        }

        if (params.toString()) {
            url += `?${params.toString()}`;
        }

        tasks = await apiCall(url);
        renderTasks();
    } catch (error) {
        console.error('Error loading tasks:', error);
        showNotification(window.TRANSLATIONS.error_loading_tasks, 'error');
    }
}

// Apply Filter
async function applyFilter(filterType, value) {
    currentFilter[filterType] = value;
    await loadTasks(currentFilter);
}

// Clear Filter
async function clearFilters() {
    currentFilter = { assigned_to: null };
    await loadTasks();
}

// Render Tasks
function renderTasks() {
    const todoColumn = document.getElementById('todoColumn');
    const inProgressColumn = document.getElementById('inProgressColumn');
    const completedColumn = document.getElementById('completedColumn');

    if (!todoColumn || !inProgressColumn || !completedColumn) {
        console.error('Task columns not found');
        return;
    }

    todoColumn.innerHTML = '';
    inProgressColumn.innerHTML = '';
    completedColumn.innerHTML = '';

    const todoTasks = tasks.filter(t => t.status === 'todo');
    const inProgressTasks = tasks.filter(t => t.status === 'in_progress');
    const completedTasks = tasks.filter(t => t.status === 'completed');

    document.getElementById('todoCount').textContent = todoTasks.length;
    document.getElementById('inProgressCount').textContent = inProgressTasks.length;
    document.getElementById('completedCount').textContent = completedTasks.length;

    if (todoTasks.length === 0) {
        todoColumn.innerHTML = `<div class="tasks-column__empty"><div class="tasks-column__empty-icon">📋</div><div>${window.TRANSLATIONS.no_tasks}</div></div>`;
    } else {
        todoTasks.forEach(task => todoColumn.appendChild(createTaskCard(task)));
    }

    if (inProgressTasks.length === 0) {
        inProgressColumn.innerHTML = `<div class="tasks-column__empty"><div class="tasks-column__empty-icon">⚡</div><div>${window.TRANSLATIONS.no_tasks}</div></div>`;
    } else {
        inProgressTasks.forEach(task => inProgressColumn.appendChild(createTaskCard(task)));
    }

    if (completedTasks.length === 0) {
        completedColumn.innerHTML = `<div class="tasks-column__empty"><div class="tasks-column__empty-icon">✓</div><div>${window.TRANSLATIONS.no_tasks}</div></div>`;
    } else {
        completedTasks.forEach(task => completedColumn.appendChild(createTaskCard(task)));
    }
}

// Create Task Card
function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = `task-card task-card--${task.priority}`;
    card.dataset.taskId = task.id;

    if (task.is_locked && !task.can_take) {
        card.classList.add('task-card--locked');
    }

    const priorityLabels = {
        'low': window.TRANSLATIONS.priority_low,
        'medium': window.TRANSLATIONS.priority_medium,
        'high': window.TRANSLATIONS.priority_high
    };

    const dueDateHTML = task.due_date ? `
        <div class="task-card__due-date ${isOverdue(task.due_date) ? 'task-card__due-date--overdue' : ''}">
            📅 ${formatDate(task.due_date)}
        </div>
    ` : '';

    const takenByHTML = task.taken_by_name ? `
        <div class="task-card__taken-by">
            <div class="task-card__avatar">${getInitials(task.taken_by_name)}</div>
            <span>🔒 ${task.taken_by_name}</span>
        </div>
    ` : '';

    const assignedHTML = task.assigned_to_name && !task.taken_by_name ? `
        <div class="task-card__assigned">
            <div class="task-card__avatar">${getInitials(task.assigned_to_name)}</div>
            <span>${window.TRANSLATIONS.assigned} ${task.assigned_to_name}</span>
        </div>
    ` : '';

    const actionsHTML = getTaskActions(task);

    card.innerHTML = `
        <div class="task-card__header">
            <div style="flex: 1;">
                <div class="task-card__title">${task.title}</div>
                ${task.is_locked && !task.can_take ? `<div class="task-card__locked-badge">🔒 ${window.TRANSLATIONS.locked}</div>` : ''}
            </div>
        </div>
        ${task.description ? `<div class="task-card__description">${task.description}</div>` : ''}
        <div class="task-card__footer">
            <div class="task-card__priority task-card__priority--${task.priority}">
                ${priorityLabels[task.priority]}
            </div>
            ${dueDateHTML}
        </div>
        ${takenByHTML}
        ${assignedHTML}
        <div class="task-card__actions">
            ${actionsHTML}
        </div>
    `;

    return card;
}

// Get Task Actions
function getTaskActions(task) {
    let actions = '';

    if (task.status === 'todo') {
        actions += `<button class="task-card__action-btn task-card__action-btn--progress" data-task-id="${task.id}" data-action="in_progress">${window.TRANSLATIONS.take_to_work}</button>`;
    } else if (task.status === 'in_progress') {
        if (task.can_take) {
            actions += `<button class="task-card__action-btn task-card__action-btn--complete" data-task-id="${task.id}" data-action="completed">${window.TRANSLATIONS.complete}</button>`;
            actions += `<button class="task-card__action-btn task-card__action-btn--todo" data-task-id="${task.id}" data-action="todo">${window.TRANSLATIONS.return}</button>`;
        } else {
            actions += `<button class="task-card__action-btn task-card__action-btn--disabled" disabled>🔒 ${window.TRANSLATIONS.locked}</button>`;
        }
    }

    if (task.can_edit) {
        actions += `<button class="task-card__action-btn task-card__action-btn--edit" data-task-id="${task.id}" data-action="edit">${window.TRANSLATIONS.edit}</button>`;
    }

    if (task.can_delete) {
        actions += `<button class="task-card__action-btn task-card__action-btn--delete" data-task-id="${task.id}" data-action="delete">${window.TRANSLATIONS.delete}</button>`;
    }

    return actions;
}

// Helper Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    return `${day}.${month}.${year}`;
}

function isOverdue(dateString) {
    const dueDate = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return dueDate < today;
}

function getInitials(name) {
    if (!name || typeof name !== 'string') return '?';
    const parts = name.trim().split(' ').filter(p => p.length > 0);
    if (parts.length >= 2 && parts[0][0] && parts[1][0]) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    if (parts.length > 0 && parts[0][0]) {
        return parts[0][0].toUpperCase();
    }
    return '?';
}

// Event Delegation для кнопок действий
function setupEventDelegation() {
    const contentWrapper = document.getElementById('content-wrapper');

    const handleClick = async (e) => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        if (btn.disabled) {
            return;
        }

        const taskId = parseInt(btn.dataset.taskId);
        const action = btn.dataset.action;

        const task = tasks.find(t => t.id === taskId);

        if (!task) {
            showNotification('Завдання не знайдено', 'error');
            return;
        }

        try {
            if (action === 'edit') {
                editTask(taskId);
            } else if (action === 'delete') {
                await deleteTask(taskId);
            } else {
                if (action === 'in_progress' || action === 'completed' || action === 'todo') {
                    if (task.is_locked && !task.can_take) {
                        showNotification('Це завдання заблоковане іншим користувачем', 'error');
                        return;
                    }
                    await updateTaskStatus(taskId, action);
                }
            }
        } catch (error) {
            console.error('Error handling action:', error);
        }
    };

    contentWrapper.addEventListener('click', handleClick);
    eventListeners.push({ element: contentWrapper, event: 'click', handler: handleClick });
}

// Добавляем обработчик для фильтра
function setupFilterHandler() {
    const filterSelect = document.getElementById('filterAssignedTo');

    if (!filterSelect) {
        console.warn('Filter select not found');
        return;
    }

    const handleFilterChange = async (e) => {
        const value = e.target.value;
        await applyFilter('assigned_to', value);
    };

    filterSelect.addEventListener('change', handleFilterChange);
    eventListeners.push({ element: filterSelect, event: 'change', handler: handleFilterChange });
}

// Update Task Status
async function updateTaskStatus(taskId, newStatus) {
    try {
        await apiCall(`${API_BASE_URL}/tasks/${taskId}/`, 'PATCH', {status: newStatus});
        await loadTasks(currentFilter);
        showNotification(window.TRANSLATIONS.status_updated, 'success');
    } catch (error) {
        const errorMessage = error.message || window.TRANSLATIONS.error_updating_status;
        showNotification(errorMessage, 'error');
    }
}

// Edit Task
function editTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) {
        showNotification('Завдання не знайдено', 'error');
        return;
    }

    if (!task.can_edit) {
        showNotification('У вас немає прав на редагування цього завдання', 'error');
        return;
    }

    isEditMode = true;
    currentTaskId = taskId;

    const taskModalTitle = document.getElementById('taskModalTitle');
    const taskModalSaveBtn = document.getElementById('taskModalSaveBtn');

    taskModalTitle.textContent = window.TRANSLATIONS.edit_task;
    taskModalSaveBtn.textContent = window.TRANSLATIONS.update;

    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.due_date || '';
    document.getElementById('taskAssignedTo').value = task.assigned_to || '';

    openTaskModal();
}

// Delete Task
async function deleteTask(taskId) {
    const task = tasks.find(t => t.id === taskId);

    if (task && !task.can_delete) {
        showNotification('У вас немає прав на видалення цього завдання', 'error');
        return;
    }

    if (!confirm(window.TRANSLATIONS.confirm_delete)) return;

    try {
        await apiCall(`${API_BASE_URL}/tasks/${taskId}/`, 'DELETE');
        await loadTasks(currentFilter);
        showNotification(window.TRANSLATIONS.task_deleted, 'success');
    } catch (error) {
        showNotification(window.TRANSLATIONS.error_deleting_task, 'error');
    }
}

// Modal Functions
function openTaskModal() {
    const taskModal = document.getElementById('taskModal');
    taskModal.classList.add('modal--active');
    document.body.style.overflow = 'hidden';
}

function closeTaskModal() {
    const taskModal = document.getElementById('taskModal');
    const taskForm = document.getElementById('taskForm');

    taskModal.classList.remove('modal--active');
    document.body.style.overflow = '';
    taskForm.reset();
    isEditMode = false;
    currentTaskId = null;
}

// Initialize
export async function init() {
    console.log('🚀 Tasks module initializing...');

    // Проверяем что мы на нужной странице
    const pageElement = document.querySelector('[data-page="tasks"]');
    if (!pageElement) {
        console.warn('⚠️ Not on tasks page');
        return;
    }

    console.log('✓ Tasks page found');

    // Загружаем данные
    await loadUsers();
    await loadTasks();

    // Настраиваем обработчики событий
    setupEventDelegation();
    setupFilterHandler();

    // Add Task Button
    const addTaskBtn = document.getElementById('addTaskBtn');
    if (addTaskBtn) {
        const handleAddTask = () => {
            const taskModalTitle = document.getElementById('taskModalTitle');
            const taskModalSaveBtn = document.getElementById('taskModalSaveBtn');
            taskModalTitle.textContent = window.TRANSLATIONS.add_task;
            taskModalSaveBtn.textContent = window.TRANSLATIONS.create;
            openTaskModal();
        };
        addTaskBtn.addEventListener('click', handleAddTask);
        eventListeners.push({ element: addTaskBtn, event: 'click', handler: handleAddTask });
    }

    // Modal Events
    const taskModalClose = document.getElementById('taskModalClose');
    const taskModalCancel = document.getElementById('taskModalCancel');
    const taskModalOverlay = document.getElementById('taskModalOverlay');

    if (taskModalClose) {
        taskModalClose.addEventListener('click', closeTaskModal);
        eventListeners.push({ element: taskModalClose, event: 'click', handler: closeTaskModal });
    }

    if (taskModalCancel) {
        taskModalCancel.addEventListener('click', closeTaskModal);
        eventListeners.push({ element: taskModalCancel, event: 'click', handler: closeTaskModal });
    }

    if (taskModalOverlay) {
        taskModalOverlay.addEventListener('click', closeTaskModal);
        eventListeners.push({ element: taskModalOverlay, event: 'click', handler: closeTaskModal });
    }

    // Form Submit
    const taskForm = document.getElementById('taskForm');
    if (taskForm) {
        const handleSubmit = async (e) => {
            e.preventDefault();

            const formData = new FormData(taskForm);
            const assignedToValue = formData.get('assigned_to');

            const data = {
                title: formData.get('title'),
                description: formData.get('description') || null,
                priority: formData.get('priority'),
                due_date: formData.get('due_date') || null,
                assigned_to: assignedToValue && assignedToValue !== '' ? parseInt(assignedToValue) : null,
            };

            if (!isEditMode) {
                data.status = 'todo';
            }

            try {
                if (isEditMode && currentTaskId) {
                    await apiCall(`${API_BASE_URL}/tasks/${currentTaskId}/`, 'PUT', data);
                    showNotification(window.TRANSLATIONS.task_updated, 'success');
                } else {
                    await apiCall(`${API_BASE_URL}/tasks/`, 'POST', data);
                    showNotification(window.TRANSLATIONS.task_created, 'success');
                }
                await loadTasks();
                closeTaskModal();
            } catch (error) {
                showNotification(window.TRANSLATIONS.error_saving_task, 'error');
            }
        };

        taskForm.addEventListener('submit', handleSubmit);
        eventListeners.push({ element: taskForm, event: 'submit', handler: handleSubmit });
    }

    // Escape key
    const handleEscape = (e) => {
        const taskModal = document.getElementById('taskModal');
        if (e.key === 'Escape' && taskModal && taskModal.classList.contains('modal--active')) {
            closeTaskModal();
        }
    };
    document.addEventListener('keydown', handleEscape);
    eventListeners.push({ element: document, event: 'keydown', handler: handleEscape });

    console.log('✓ Tasks module initialized');
}

// Cleanup
export function cleanup() {
    console.log('🧹 Tasks module cleanup');

    // Удаляем все обработчики событий
    eventListeners.forEach(({ element, event, handler }) => {
        element.removeEventListener(event, handler);
    });
    eventListeners = [];

    // Очищаем состояние
    tasks = [];
    currentTaskId = null;
    isEditMode = false;
    currentFilter = { assigned_to: null };
}