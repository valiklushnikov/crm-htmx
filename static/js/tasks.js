// API Configuration
const API_BASE_URL = '/api/auth';

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
            const errorData = await response.json();

            // Handle validation errors for assigned_to
            if (errorData.assigned_to) {
                throw new Error(`Помилка призначення: ${errorData.assigned_to[0]}`);
            }

            throw new Error(errorData.detail || 'Помилка запиту');
        }
        return method === 'DELETE' ? null : await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// DOM Elements
const addTaskBtn = document.getElementById('addTaskBtn');
const taskModal = document.getElementById('taskModal');
const taskModalOverlay = document.getElementById('taskModalOverlay');
const taskModalClose = document.getElementById('taskModalClose');
const taskModalCancel = document.getElementById('taskModalCancel');
const taskForm = document.getElementById('taskForm');
const taskModalTitle = document.getElementById('taskModalTitle');
const taskModalSaveBtn = document.getElementById('taskModalSaveBtn');

// Columns
const todoColumn = document.getElementById('todoColumn');
const inProgressColumn = document.getElementById('inProgressColumn');
const completedColumn = document.getElementById('completedColumn');

// State
let tasks = [];
let currentTaskId = null;
let isEditMode = false;



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

    // Clear existing options except the first one (placeholder)
    select.innerHTML = `<option value="">${window.TRANSLATIONS.not_assigned}</option>`;

    // Add user options
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
function applyFilter(filterType, value) {
    currentFilter[filterType] = value;
    loadTasks(currentFilter);
}

// Clear Filter
function clearFilters() {
    currentFilter = { assigned_to: null };
    loadTasks();
}

// Render Tasks
function renderTasks() {
    // Clear columns
    todoColumn.innerHTML = '';
    inProgressColumn.innerHTML = '';
    completedColumn.innerHTML = '';

    // Filter tasks by status
    const todoTasks = tasks.filter(t => t.status === 'todo');
    const inProgressTasks = tasks.filter(t => t.status === 'in_progress');
    const completedTasks = tasks.filter(t => t.status === 'completed');

    // Update counts
    document.getElementById('todoCount').textContent = todoTasks.length;
    document.getElementById('inProgressCount').textContent = inProgressTasks.length;
    document.getElementById('completedCount').textContent = completedTasks.length;

    // Show empty state BEFORE adding tasks OR add tasks
    if (todoTasks.length === 0) {
        todoColumn.innerHTML = `<div class="tasks-column__empty"><div class="tasks-column__empty-icon">📋</div><div>${window.TRANSLATIONS.no_tasks}</div></div>`;
    } else {
        todoTasks.forEach(task => {
            todoColumn.appendChild(createTaskCard(task));
        });
    }

    if (inProgressTasks.length === 0) {
        inProgressColumn.innerHTML = `<div class="tasks-column__empty"><div class="tasks-column__empty-icon">⚡</div><div>${window.TRANSLATIONS.no_tasks}</div></div>`;
    } else {
        inProgressTasks.forEach(task => {
            inProgressColumn.appendChild(createTaskCard(task));
        });
    }

    if (completedTasks.length === 0) {
        completedColumn.innerHTML = `<div class="tasks-column__empty"><div class="tasks-column__empty-icon">✓</div><div>${window.TRANSLATIONS.no_tasks}</div></div>`;
    } else {
        completedTasks.forEach(task => {
            completedColumn.appendChild(createTaskCard(task));
        });
    }
}

// Create Task Card
function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = `task-card task-card--${task.priority}`;
    card.dataset.taskId = task.id;

    // Додаємо клас для заблокованих завдань
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

    // Показуємо хто взяв завдання в роботу
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

// Get Task Actions based on status and permissions
function getTaskActions(task) {
    let actions = '';

    // Кнопки зміни статусу
    if (task.status === 'todo') {
        actions += `<button class="task-card__action-btn task-card__action-btn--progress" onclick="updateTaskStatus(${task.id}, 'in_progress')">${window.TRANSLATIONS.take_to_work}</button>`;
    } else if (task.status === 'in_progress') {
        if (task.can_take) {
            // Тільки той хто взяв завдання може його завершити або повернути
            actions += `<button class="task-card__action-btn task-card__action-btn--complete" onclick="updateTaskStatus(${task.id}, 'completed')">${window.TRANSLATIONS.complete}</button>`;
            actions += `<button class="task-card__action-btn task-card__action-btn--todo" onclick="updateTaskStatus(${task.id}, 'todo')">${window.TRANSLATIONS.return}</button>`;
        } else {
            // Завдання заблоковане іншим користувачем
            actions += `<button class="task-card__action-btn task-card__action-btn--disabled" disabled>🔒 ${window.TRANSLATIONS.locked}</button>`;
        }
    }

    // Кнопки редагування та видалення тільки для автора
    if (task.can_edit) {
        actions += `<button class="task-card__action-btn task-card__action-btn--edit" onclick="editTask(${task.id})">${window.TRANSLATIONS.edit}</button>`;
    }

    if (task.can_delete) {
        actions += `<button class="task-card__action-btn task-card__action-btn--delete" onclick="deleteTask(${task.id})">${window.TRANSLATIONS.delete}</button>`;
    }

    return actions;
}

// Update Task Status
async function updateTaskStatus(taskId, newStatus) {
    try {
        await apiCall(`${API_BASE_URL}/tasks/${taskId}/`, 'PATCH', { status: newStatus });
        await loadTasks();
        showNotification(window.TRANSLATIONS.status_updated, 'success');
    } catch (error) {
        // Показуємо конкретне повідомлення про помилку, якщо воно є
        const errorMessage = error.message || window.TRANSLATIONS.error_updating_status;
        showNotification(errorMessage, 'error');
    }
}

// Edit Task
function editTask(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    isEditMode = true;
    currentTaskId = taskId;

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
    if (!confirm(window.TRANSLATIONS.confirm_delete)) return;

    try {
        await apiCall(`${API_BASE_URL}/tasks/${taskId}/`, 'DELETE');
        await loadTasks();
        showNotification(window.TRANSLATIONS.task_deleted, 'success');
    } catch (error) {
        showNotification(window.TRANSLATIONS.error_deleting_task, 'error');
    }
}

// Open Task Modal
function openTaskModal() {
    taskModal.classList.add('modal--active');
    document.body.style.overflow = 'hidden';
}

// Close Task Modal
function closeTaskModal() {
    taskModal.classList.remove('modal--active');
    document.body.style.overflow = '';
    taskForm.reset();
    isEditMode = false;
    currentTaskId = null;
}

// Add Task Button
addTaskBtn.addEventListener('click', () => {
    taskModalTitle.textContent = window.TRANSLATIONS.add_task;
    taskModalSaveBtn.textContent = window.TRANSLATIONS.create;
    openTaskModal();
});

// Close Modal Events
taskModalClose.addEventListener('click', closeTaskModal);
taskModalCancel.addEventListener('click', closeTaskModal);
taskModalOverlay.addEventListener('click', closeTaskModal);

// Form Submit
taskForm.addEventListener('submit', async (e) => {
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

    // If not editing, set status to todo
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
});

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

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    const bgColor = type === 'success' ? '#28A745' : '#DC3545';
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: ${bgColor};
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 3000;
        animation: slideInRight 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && taskModal.classList.contains('modal--active')) {
        closeTaskModal();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadUsers();  // Load users first
    await loadTasks();  // Then load tasks
});
