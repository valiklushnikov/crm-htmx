// Helper function to get CSRF token from cookies
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

// Auto-refresh JWT token before it expires
async function refreshAccessToken() {
    try {
        console.log('Refreshing access token...');
        const response = await fetch('/api/auth/token/refresh/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            console.log('✓ Access token refreshed successfully');
            return true;
        } else {
            console.error('Failed to refresh token (status:', response.status, ')');
            if (response.status === 401) {
                console.error('Redirecting to login...');
                window.location.href = '/accounts/login/';
            }
            return false;
        }
    } catch (error) {
        console.error('Error refreshing token:', error);
        return false;
    }
}

// Token refresh is now handled lazily by chat.js and on-demand by middleware
// No need for proactive interval-based refresh

const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');

// Ключ для localStorage
const SIDEBAR_STATE_KEY = 'sidebarCollapsed';

// Функция для получения состояния из localStorage
function getSidebarState() {
    const saved = localStorage.getItem(SIDEBAR_STATE_KEY);
    // По умолчанию sidebar свернут (true)
    return saved === null ? true : saved === 'true';
}

// Функция для сохранения состояния в localStorage
function saveSidebarState(isCollapsed) {
    localStorage.setItem(SIDEBAR_STATE_KEY, isCollapsed.toString());
}

// Применяем сохраненное состояние при загрузке страницы
function initSidebar() {
    const isCollapsed = getSidebarState();
    if (isCollapsed) {
        sidebar.classList.add('sidebar--collapsed');
    } else {
        sidebar.classList.remove('sidebar--collapsed');
    }
}

// Инициализация при загрузке
initSidebar();

// Sidebar Toggle с сохранением состояния
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('sidebar--collapsed');
    const isCollapsed = sidebar.classList.contains('sidebar--collapsed');
    saveSidebarState(isCollapsed);
});

// User Profile Modal
const userProfileModal = document.getElementById('userProfileModal');
const profileModalOverlay = document.getElementById('profileModalOverlay');
const profileModalClose = document.getElementById('profileModalClose');
const headerUserDropdown = document.querySelector('.header__user-dropdown');
const headerUser = document.querySelector('.header__user');

// Profile views
const profileView = document.getElementById('profileView');
const profileEditForm = document.getElementById('profileEditForm');
const profilePasswordForm = document.getElementById('profilePasswordForm');

// Profile buttons
const editProfileBtn = document.getElementById('editProfileBtn');
const changePasswordBtn = document.getElementById('changePasswordBtn');
const cancelEditBtn = document.getElementById('cancelEditBtn');
const cancelPasswordBtn = document.getElementById('cancelPasswordBtn');

// Avatar
const changeAvatarBtn = document.getElementById('changeAvatarBtn');
const avatarInput = document.getElementById('avatarInput');
const profileAvatar = document.getElementById('profileAvatar');

// Open profile modal
if (headerUser) {
    console.log('headerUser element found, adding click listener');
    headerUser.addEventListener('click', async () => {
        userProfileModal.classList.add('modal--active');
        showProfileView();
    });
}

// Close profile modal
if (profileModalClose) {
    profileModalClose.addEventListener('click', () => {
        userProfileModal.classList.remove('modal--active');
        showProfileView();
    });
}

if (profileModalOverlay) {
    profileModalOverlay.addEventListener('click', () => {
        userProfileModal.classList.remove('modal--active');
        showProfileView();
    });
}

// Show profile view
async function showProfileView() {
    profileView.style.display = 'flex';
    profileEditForm.style.display = 'none';
    profilePasswordForm.style.display = 'none';
    await loadUserProfile()
}

// Show edit form
if (editProfileBtn) {
    editProfileBtn.addEventListener('click', () => {
        const firstName = document.getElementById('profileFirstName').textContent;
        const lastName = document.getElementById('profileLastName').textContent;
        
        document.getElementById('editFirstName').value = firstName;
        document.getElementById('editLastName').value = lastName;
        
        profileView.style.display = 'none';
        profileEditForm.style.display = 'flex';
    });
}

// Show password form
if (changePasswordBtn) {
    changePasswordBtn.addEventListener('click', () => {
        profileView.style.display = 'none';
        profilePasswordForm.style.display = 'flex';
    });
}

// Cancel edit
if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', () => {
        showProfileView();
    });
}

// Cancel password change
if (cancelPasswordBtn) {
    cancelPasswordBtn.addEventListener('click', () => {
        profilePasswordForm.reset();
        showProfileView();
    });
}

// Load user profile
async function loadUserProfile() {
    try {
        const response = await fetch('/api/auth/profile/', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            const data = await response.json();
            
            // Update profile view
            document.getElementById('profileFirstName').textContent = data.first_name || '-';
            document.getElementById('profileLastName').textContent = data.last_name || '-';
            document.getElementById('profileEmail').textContent = data.email || '-';
            
            if (data.date_joined) {
                const date = new Date(data.date_joined);
                document.getElementById('profileDateJoined').textContent = date.toLocaleDateString('uk-UA');
            }
            
            // Update avatar
            if (data.avatar) {
                profileAvatar.src = data.avatar;
            }
        } else {
            console.error('Failed to load profile');
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

// Handle profile edit form submit
if (profileEditForm) {
    profileEditForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const firstName = document.getElementById('editFirstName').value;
        const lastName = document.getElementById('editLastName').value;
        
        try {
            const response = await fetch('/api/auth/profile/', {
                method: 'PATCH',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    first_name: firstName,
                    last_name: lastName
                })
            });

            if (response.ok) {
                await loadUserProfile();
                showProfileView();
                
                // Update header name
                const headerUserName = document.querySelector('.header__user-name');
                if (headerUserName) {
                    headerUserName.textContent = `${firstName} ${lastName}`;
                }
                
                alert('Профіль успішно оновлено');
            } else {
                const error = await response.json();
                alert('Помилка оновлення профілю: ' + JSON.stringify(error));
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            alert('Помилка оновлення профілю');
        }
    });
}

// Handle password change form submit
if (profilePasswordForm) {
    profilePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const oldPassword = document.getElementById('oldPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const newPasswordConfirm = document.getElementById('newPasswordConfirm').value;
        
        if (newPassword !== newPasswordConfirm) {
            alert('Нові паролі не співпадають');
            return;
        }
        
        try {
            const response = await fetch('/api/auth/change-password/', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    old_password: oldPassword,
                    new_password: newPassword,
                    new_password_confirm: newPasswordConfirm
                })
            });

            if (response.ok) {
                profilePasswordForm.reset();
                showProfileView();
                alert('Пароль успішно змінено');
            } else {
                const error = await response.json();
                let errorMessage = 'Помилка зміни пароля';
                
                if (error.old_password) {
                    errorMessage = error.old_password[0];
                } else if (error.new_password) {
                    errorMessage = error.new_password[0];
                } else if (error.new_password_confirm) {
                    errorMessage = error.new_password_confirm[0];
                }
                
                alert(errorMessage);
            }
        } catch (error) {
            console.error('Error changing password:', error);
            alert('Помилка зміни пароля');
        }
    });
}

// Handle avatar change
if (changeAvatarBtn && avatarInput) {
    changeAvatarBtn.addEventListener('click', () => {
        avatarInput.click();
    });
    
    avatarInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Будь ласка, виберіть файл зображення');
            return;
        }
        
        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            alert('Розмір файлу не повинен перевищувати 5MB');
            return;
        }
        
        const formData = new FormData();
        formData.append('avatar', file);
        
        try {
            const response = await fetch('/api/auth/profile/', {
                method: 'PATCH',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                if (data.avatar) {
                    profileAvatar.src = data.avatar;
                    
                    // Update header avatar
                    const headerAvatar = document.querySelector('.header__user-avatar');
                    if (headerAvatar) {
                        headerAvatar.src = data.avatar;
                    }
                }
                alert('Аватар успішно оновлено');
            } else {
                const error = await response.json();
                alert('Помилка завантаження аватара: ' + JSON.stringify(error));
            }
        } catch (error) {
            console.error('Error uploading avatar:', error);
            alert('Помилка завантаження аватара');
        }
    });
}
