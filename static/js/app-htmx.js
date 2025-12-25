/**
 * app-htmx.js
 * Minimal JavaScript for HTMX-powered dashboard
 */

// ============================================
// Context Menu
// ============================================
let currentEmployeeId = null;

function showContextMenu(event, employeeId) {
    event.preventDefault();
    event.stopPropagation();

    currentEmployeeId = employeeId;

    const contextMenu = document.getElementById('contextMenu');
    contextMenu.style.left = event.clientX + 'px';
    contextMenu.style.top = event.clientY + 'px';
    contextMenu.classList.add('context-menu--active');

    setTimeout(() => {
        const rect = contextMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            contextMenu.style.left = `${event.clientX - rect.width}px`;
        }
        if (rect.bottom > window.innerHeight) {
            contextMenu.style.top = `${event.clientY - rect.height}px`;
        }
    }, 0);
}

function viewEmployeeContext(employeeId) {
    htmx.ajax('GET', `/employee/${employeeId}/`, {
        target: '#modal-container',
        swap: 'innerHTML'
    });
    hideContextMenu();
}

function editEmployeeContext(employeeId) {
    htmx.ajax('GET', `/employee/form/?action=edit&employee_id=${employeeId}`, {
        target: '#modal-container',
        swap: 'innerHTML'
    });
    hideContextMenu();

}

function deleteEmployeeContext(employeeId) {
    if (confirm(window.EMPLOYEE_TRANSLATIONS?.delete_employee || 'Видалити співробітника?')) {
        htmx.ajax('DELETE', `/api/auth/profile/${employeeId}/delete/`, {
            target: '#employees-table-container',
            swap: 'innerHTML'
        }).then(() => {
            htmx.trigger(document.body, 'employeeDeleted');
        });
    }
    hideContextMenu();
}

function hideContextMenu() {
    const contextMenu = document.getElementById('contextMenu');
    contextMenu?.classList.remove('context-menu--active');
    document.body.style.overflow = 'hidden';
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.context-menu') && !e.target.closest('.employees-table__menu-btn')) {
        hideContextMenu();
    }
});

// ============================================
// Dynamic Contact Forms
// ============================================
document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        if (evt.detail.target.id === 'modal-container') {
            initializeContactFormset();
            initializeFlatpickr();
        }

        if (evt.detail.target.id === 'filterDropdownMenu') {
            initializeFilterDropdown();
        }
    });
});

function initializeContactFormset() {
    const addBtn = document.getElementById("add-contact");
    const list = document.getElementById("contacts-list");
    const template = document.querySelector("#contact-template .contacts__item");

    if (addBtn && list && template) {
        const newAddBtn = addBtn.cloneNode(true);
        addBtn.parentNode.replaceChild(newAddBtn, addBtn);

        newAddBtn.addEventListener("click", () => {
            const formCount = document.querySelector('input[name$="-TOTAL_FORMS"]');

            if (!formCount) {
                console.error("TOTAL_FORMS not found!");
                return;
            }

            const current = parseInt(formCount.value, 10);
            const newForm = template.cloneNode(true);

            newForm.querySelectorAll("input, select").forEach(el => {
                el.name = el.name.replace(/__prefix__/g, current);
                if (el.id) {
                    el.id = el.id.replace(/__prefix__/g, current);
                }
                if (el.type !== "hidden") {
                    el.value = "";
                }
            });

            list.appendChild(newForm);
            formCount.value = current + 1;
        });
    }
}

// ============================================
// Flatpickr
// ============================================
function initializeFlatpickr() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.classList.contains('flatpickr-input')) {
            flatpickr(input, {
                dateFormat: "Y-m-d",
                allowInput: true
            });
        }
    });
}

// ============================================
// Filter Dropdown
// ============================================
function initializeFilterDropdown() {
    const filterDropdownMenu = document.getElementById('filterDropdownMenu');
    if (!filterDropdownMenu) return;

    // Показываем меню
    filterDropdownMenu.classList.add('filter-dropdown__menu--active');

    // Закрытие при клике вне
    const closeOnOutsideClick = (e) => {
        const filterToggleBtn = document.getElementById('filterToggleBtn');
        if (filterDropdownMenu &&
            !filterDropdownMenu.contains(e.target) &&
            !filterToggleBtn?.contains(e.target)) {
            filterDropdownMenu.classList.remove('filter-dropdown__menu--active');
            document.removeEventListener('click', closeOnOutsideClick);
        }
    };

    // Добавляем обработчик с небольшой задержкой
    setTimeout(() => {
        document.addEventListener('click', closeOnOutsideClick);
    }, 100);
}

// Check if filters are active on page load
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const statusParams = urlParams.getAll('status');
    const filterToggleBtn = document.getElementById('filterToggleBtn');

    if (statusParams.length > 0 && filterToggleBtn) {
        filterToggleBtn.classList.add('employees__filter--active');
    }
});

// ============================================
// Search
// ============================================
function clearSearchInput() {
    const input = document.getElementById('searchInput');
    const clearBtn = document.querySelector('.header__search-clear');

    searchInput.addEventListener('input', () => {
        if (searchInput.value.trim() !== '') {
            clearBtn.classList.remove('hide');
        } else {
            clearBtn.classList.add('hide');
        }
    });
    if (input) {
        input.value = '';
        // Trigger HTMX request
        htmx.trigger(input, 'keyup');
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.delete('q');
    }
}

// Make globally available
window.clearSearchInput = clearSearchInput;

// ============================================
// PDF Export
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    const pdfBtn = document.getElementById('pdfExportBtn');
    if (pdfBtn) {
        pdfBtn.addEventListener('click', function(e) {
            const textSpan = this.querySelector('.pdf-btn-text');
            const loadingSpan = this.querySelector('.pdf-btn-loading');

            if (textSpan && loadingSpan) {
                textSpan.style.display = 'none';
                loadingSpan.style.display = 'flex';
                this.style.pointerEvents = 'none';
                this.style.opacity = '0.7';

                setTimeout(() => {
                    textSpan.style.display = 'inline';
                    loadingSpan.style.display = 'none';
                    this.style.pointerEvents = 'auto';
                    this.style.opacity = '1';
                }, 3000);
            }
        });
    }
});

// ============================================
// Notifications
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    const notification = sessionStorage.getItem('notification');
    if (notification) {
        const {message, type} = JSON.parse(notification);
        showNotification(message, type || 'success');
        sessionStorage.removeItem('notification');
    }
});

// function showNotification(message, type = 'success') {
//     const colors = {
//         success: '#28A745',
//         error: '#DC3545',
//         warning: '#FFC107',
//         info: '#17A2B8'
//     };
//
//     const notification = document.createElement('div');
//     notification.style.cssText = `
//         position: fixed;
//         top: 20px;
//         right: 20px;
//         background-color: ${colors[type] || colors.success};
//         color: white;
//         padding: 16px 24px;
//         border-radius: 8px;
//         box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
//         z-index: 3000;
//         animation: slideInRight 0.3s ease;
//     `;
//     notification.textContent = message;
//     document.body.appendChild(notification);
//
//     setTimeout(() => {
//         notification.style.animation = 'slideOutRight 0.3s ease';
//         setTimeout(() => {
//             if (document.body.contains(notification)) {
//                 document.body.removeChild(notification);
//             }
//         }, 300);
//     }, 3000);
// }
//
// window.showNotification = showNotification;

// ============================================
// HTMX Event Handlers
// ============================================
document.body.addEventListener('htmx:beforeRequest', function(evt) {
    const target = evt.detail.target;
    if (target) {
        target.classList.add('htmx-loading');
    }
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    const target = evt.detail.target;
    if (target) {
        target.classList.remove('htmx-loading');
    }
});

document.body.addEventListener('htmx:responseError', function(evt) {
    const status = evt.detail.xhr.status;

    if (status === 401) {
        window.location.href = '/accounts/login/';
    } else if (status === 423) {
        showNotification('Цей співробітник зараз редагується іншим користувачем', 'warning');
    } else if (status === 404) {
        showNotification('Ресурс не знайдено', 'error');
    } else {
        showNotification('Виникла помилка. Спробуйте пізніше', 'error');
    }
});

// ============================================
// Animation styles
// ============================================
if (!document.getElementById('notification-animations')) {
    const style = document.createElement('style');
    style.id = 'notification-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .htmx-loading {
            opacity: 0.6;
            pointer-events: none;
        }
    `;
    document.head.appendChild(style);
}

// Filter functionality with HTMX
document.body.addEventListener('htmx:afterSwap', () => {
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const filterDropdownMenu = document.getElementById('filterDropdownMenu');
    const filterCloseBtn = document.getElementById('filterCloseBtn');
    const filterForm = document.getElementById('filterForm');
    const filterClearBtn = document.getElementById('filterClearBtn');
    const filterApplyBtn = document.getElementById('filterApplyBtn');

    if (!filterToggleBtn || !filterDropdownMenu) return;

    filterToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        filterDropdownMenu.classList.toggle('filter-dropdown__menu--active');
    });

    if (filterCloseBtn) {
        filterCloseBtn.addEventListener('click', () => {
            filterDropdownMenu.classList.remove('filter-dropdown__menu--active');
        });
    }

    document.addEventListener('click', (e) => {
        if (!filterDropdownMenu.contains(e.target) && !filterToggleBtn.contains(e.target)) {
            filterDropdownMenu.classList.remove('filter-dropdown__menu--active');
        }
    });

    if (filterClearBtn) {
        filterClearBtn.addEventListener('click', () => {
            const checkboxes = filterForm.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = false);
            filterToggleBtn.classList.remove('employees__filter--active');

            // Оновлюємо таблицю без фільтрів
            const url = new URL(window.location.href);
            url.searchParams.delete('status');
        });
    }

    if (filterApplyBtn) {
        filterApplyBtn.addEventListener('click', () => {
            const checkboxes = filterForm.querySelectorAll('input[type="checkbox"]:checked');
            const selectedStatuses = Array.from(checkboxes).map(cb => cb.value);

            if (selectedStatuses.length > 0) {
                filterToggleBtn.classList.add('employees__filter--active');
            } else {
                filterToggleBtn.classList.remove('employees__filter--active');
            }

            const url = new URL(window.location.href);
            url.searchParams.delete('status');
            selectedStatuses.forEach(status => {
                url.searchParams.append('status', status);
            });

            htmx.ajax('GET', url.toString(), {
                target: '#employees-table-content',
                swap: 'innerHTML',
                indicator: '#table-loading'
            });

            filterDropdownMenu.classList.remove('filter-dropdown__menu--active');
        });
    }

    // Check if filters are active on page load
    const urlParams = new URLSearchParams(window.location.search);
    const statusParams = urlParams.getAll('status');

    if (statusParams.length > 0) {
        filterToggleBtn.classList.add('employees__filter--active');

        const checkboxes = filterForm.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            if (statusParams.includes(checkbox.value)) {
                checkbox.checked = true;
            }
        });
    }
});