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

// Configure HTMX
document.addEventListener('DOMContentLoaded', () => {
    // Додаємо CSRF токен до всіх HTMX запитів
    document.body.addEventListener('htmx:configRequest', (event) => {
        event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
    });
});

// DOM Elements
const addEmployeeBtn = document.getElementById('addEmployeeBtn');
const employeeModal = document.getElementById('employeeModal');
const modalOverlay = document.getElementById('modalOverlay');
const modalClose = document.getElementById('modalClose');
const modalCancel = document.getElementById('modalCancel');
const employeeForm = document.getElementById('employeeForm');
const modalTitle = document.getElementById('modalTitle');
const modalSaveBtn = document.getElementById('modalSaveBtn');

// View Employee Modal Elements
const viewEmployeeModal = document.getElementById('viewEmployeeModal');
const viewModalOverlay = document.getElementById('viewModalOverlay');
const viewModalClose = document.getElementById('viewModalClose');
const employeeCard = document.getElementById('employeeCard');

// Context Menu Elements
const contextMenu = document.getElementById('contextMenu');


// State
let currentEmployeeId = null;
let isEditMode = false;



// Render Employees Table
function renderEmployees() {
    const tbody = employeesTable.querySelector('.employees-table__body');

    // Add event listeners to menu buttons
    const menuButtons = tbody.querySelectorAll('.employees-table__menu-btn');
    menuButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const employeeId = parseInt(btn.dataset.employeeId);
            showContextMenu(e, employeeId);
        });
    });

    tbody.addEventListener('click', (e) => {
        if (e.target.closest('.employees-table__menu-btn')) {
            return;
        }

        const row = e.target.closest('.employees-table__row');
        if (row && row.dataset.employeeId) {
            const employeeId = parseInt(row.dataset.employeeId);
            openViewModal(employeeId);
        }
    });

}

// Open Modal
async function openModal(mode = 'add', employeeId = null) {
    isEditMode = mode === 'edit';
    currentEmployeeId = employeeId;

    // Якщо редагуємо існуючого співробітника, спробуємо встановити блокування
    if (isEditMode && employeeId) {
        const lockResult = await lockEmployee(employeeId);
        if (!lockResult) {
            // Не вдалося встановити блокування - співробітник редагується іншим користувачем
            showNotification('Цей співробітник зараз редагується іншим користувачем. Спробуйте пізніше.', 'error');
            return;
        }
    }

    employeeModal.classList.add('modal--active');
    document.body.style.overflow = 'hidden';

    const oldHiddenFields = employeeForm.querySelectorAll('input[type="hidden"][name*="employee"]');
    const label = document.querySelector('label[for="workingStatus"]');
    const formGroup = label.closest('.form-group');
    if (label && isEditMode) {

        if (formGroup) {
            formGroup.style.display = 'flex';
        }
    } else {
        if (formGroup) {
            formGroup.style.display = 'none';
        }
    }

    oldHiddenFields.forEach(field => field.remove());

    if (isEditMode && employeeId) {
        modalTitle.textContent = window.EMPLOYEE_TRANSLATIONS.update_employee;
        modalSaveBtn.textContent = window.EMPLOYEE_TRANSLATIONS.update;
        modalCancel.textContent = window.EMPLOYEE_TRANSLATIONS.cancel;

        const updateHidden = document.createElement('input');
        updateHidden.type = 'hidden';
        updateHidden.name = 'update_employee';
        updateHidden.value = '1';
        employeeForm.appendChild(updateHidden);

        const idHidden = document.createElement('input');
        idHidden.type = 'hidden';
        idHidden.name = 'employee_id';
        idHidden.value = employeeId;
        employeeForm.appendChild(idHidden);
        await loadEmployeeData(employeeId);

    } else {
        modalTitle.textContent = window.EMPLOYEE_TRANSLATIONS.add_employee;
        modalSaveBtn.textContent = window.EMPLOYEE_TRANSLATIONS.save;
        modalCancel.textContent = window.EMPLOYEE_TRANSLATIONS.cancel;
        employeeForm.reset();

        const createHidden = document.createElement('input');
        createHidden.type = 'hidden';
        createHidden.name = 'create_employee';
        createHidden.value = '1';
        employeeForm.appendChild(createHidden);
    }
}

async function loadEmployeeData(employeeId) {
    try {
        const response = await fetch(`/api/auth/profile/${employeeId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                console.error('Unauthorized - JWT token missing or invalid');
                showNotification(window.EMPLOYEE_TRANSLATIONS.auth_error, 'error');
                return;
            }
            if (response.status === 404) {
                showNotification(window.EMPLOYEE_TRANSLATIONS.employee_not_found, 'error');
                return;
            }
            throw new Error('Failed to load employee data');
        }

        const data = await response.json();
        fillFormWithData(data);
    } catch (error) {
        console.error('Error loading employee data:', error);
        showNotification(window.EMPLOYEE_TRANSLATIONS.error_loading_employee, 'error');
    }
}

function fillFormWithData(data) {
    setFieldValue('firstName', data.first_name);
    setFieldValue('lastName', data.last_name);
    setFieldValue('age', data.age);

    setFieldValue('isStudent', boolToString(data.is_student));
    setFieldValue('studentEndDate', data.student_end_date);
    setFieldValue('pesel', data.pesel);
    setFieldValue('peselUrk', boolToString(data.pesel_urk));
    setFieldValue('workplace', data.workplace);
    setFieldValue('pit2', boolToString(data.pit_2));
    setFieldValue('workingStatus', data.working_status);


    if (data.employment_period && data.employment_period.length > 0) {
        const period = data.employment_period[0];
        setFieldValue('employmentStartDate', period.start_date);
        setFieldValue('employmentEndDate', period.end_date);
    }

    if (data.documents && data.documents.length > 0) {
        const doc = data.documents[0];
        setFieldValue('docType', doc.doc_type);
        setFieldValue('docNumber', doc.number);
        setFieldValue('docValidUntil', doc.valid_until);
    }

    if (data.work_permits && data.work_permits.length > 0) {
        const permit = data.work_permits[0];
        setFieldValue('workPermitType', permit.doc_type);
        setFieldValue('workPermitEndDate', permit.end_date);
    }

    if (data.card_submissions && data.card_submissions.length > 0) {
        const submission = data.card_submissions[0];
        setFieldValue('cardSubmissionType', submission.doc_type);
        setFieldValue('cardSubmissionStartDate', submission.start_date);
    }

    if (data.contracts && data.contracts.length > 0) {
        const contract = data.contracts[0];
        setFieldValue('contractType', contract.contract_type);
    }

    if (data.sanepids && data.sanepids.length > 0) {
        const sanepid = data.sanepids[0];
        setFieldValue('sanepidStatus', sanepid.status);
        setFieldValue('sanepidEndDate', sanepid.end_date);
    }

    if (data.contacts && data.contacts.length > 0) {
        fillContacts(data.contacts);
    }

    setFieldValue('additionalInfo', data.additional_information);
}

function setFieldValue(fieldId, value) {
    const field = document.getElementById(fieldId);
    if (field && value !== null && value !== undefined) {
        field.value = value;
    }
}

function fillContacts(contactList) {
    const list = document.getElementById("contacts-list");
    const template = document.querySelector("#contact-template .contacts__item");
    const totalForms = document.querySelector('input[name="contacts-TOTAL_FORMS"]');
    const initialForms = document.querySelector('input[name="contacts-INITIAL_FORMS"]');

    list.innerHTML = "";

    contactList.forEach((item, index) => {
        const form = template.cloneNode(true);

        form.querySelectorAll("input, select").forEach(el => {
            el.name = el.name.replace("__prefix__", index);
            if (el.id) el.id = el.id.replace("__prefix__", index);

            if (el.name.endsWith("-contact_type")) {
                el.value = item.contact_type;
            } else if (el.name.endsWith("-value")) {
                el.value = item.value;
            } else if (el.name.endsWith("-id")) {
                el.value = item.id;
            } else if (el.name.endsWith("-employee")) {
                el.value = item.employee;
            }
        });

        list.appendChild(form);
    });

    if (totalForms) totalForms.value = contactList.length;
    if (initialForms) initialForms.value = contactList.length;
}

function boolToString(value) {
    if (value === true) return 'true';
    if (value === false) return 'false';
    return '';
}

// Close Modal
async function closeModal() {
    // Знімаємо блокування при закритті модального вікна
    if (currentEmployeeId) {
        await unlockEmployee(currentEmployeeId);
    }
    
    employeeModal.classList.remove('modal--active');
    document.body.style.overflow = '';
    employeeForm.reset();
    isEditMode = false;
    currentEmployeeId = null;
}

// Lock Employee
async function lockEmployee(employeeId) {
    try {
        const response = await fetch(window.LOCK_EMPLOYEE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ employee_id: employeeId }),
            credentials: 'include'
        });
        
        if (response.status === 423) {
            // Співробітник заблокований іншим користувачем
            return false;
        }
        
        return response.ok;
    } catch (error) {
        console.error('Error locking employee:', error);
        return false;
    }
}

// Unlock Employee
async function unlockEmployee(employeeId) {
    try {
        await fetch(window.UNLOCK_EMPLOYEE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ employee_id: employeeId }),
            credentials: 'include'
        });
    } catch (error) {
        console.error('Error unlocking employee:', error);
    }
}

// Open View Employee Modal
async function openViewModal(employeeId) {
    // Check if translations are loaded
    if (typeof window.EMPLOYEE_TRANSLATIONS === 'undefined') {
        console.error('EMPLOYEE_TRANSLATIONS not loaded');
        alert('Помилка завантаження перекладів');
        return;
    }
    
    try {
        const response = await fetch(`/api/auth/profile/${employeeId}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                console.error('Unauthorized - JWT token missing or invalid');
                showNotification(window.EMPLOYEE_TRANSLATIONS.auth_error, 'error');
                return;
            }
            if (response.status === 404) {
                showNotification(window.EMPLOYEE_TRANSLATIONS.employee_not_found, 'error');
                return;
            }
            throw new Error('Failed to load employee data');
        }

        const employee = await response.json();

        if (!employee) return;

        // Helper function to format date
        const formatDate = (dateStr) => {
            if (!dateStr) return window.EMPLOYEE_TRANSLATIONS.not_specified;
            const date = new Date(dateStr);
            return date.toLocaleDateString('uk-UA', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        };

        const boolCast = (value) => {
            return value ? window.EMPLOYEE_TRANSLATIONS.yes : window.EMPLOYEE_TRANSLATIONS.no;
        }

        const activeMapper = (value) => {
            const statuses = {
                'Pracujący': 'works',
                'Zwolniony': 'fired',
                'Umowa o prace': 'contract',
                'Zmiana stanowiska': 'shift'
            }
            return statuses[value];
        }

        const statusMapper = (value) => {
            const statuses = {
                'Pracujący': window.EMPLOYEE_TRANSLATIONS.employed,
                'Zwolniony': window.EMPLOYEE_TRANSLATIONS.fired,
                'Umowa o prace': window.EMPLOYEE_TRANSLATIONS.employment_contract,
                'Zmiana stanowiska': window.EMPLOYEE_TRANSLATIONS.position_change
            }
            return statuses[value];
        }

        // Helper function to check if date is expired
        const isExpired = (dateStr) => {
            if (!dateStr) return false;
            return new Date(dateStr) < new Date();
        };

        // Format full name
        const fullName = `${employee.first_name || ''} ${employee.last_name || ''}`.trim() || window.EMPLOYEE_TRANSLATIONS.name_not_specified;

        // Generate Employment Periods HTML
        const employmentPeriodsHTML = employee.employment_period && employee.employment_period.length > 0
            ? employee.employment_period.map(period => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.start_date}</span>
                            <span class="employee-profile__field-value">${formatDate(period?.start_date)}</span>
                        </div>
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.end_date}</span>
                            <span class="employee-profile__field-value">${formatDate(period?.end_date)}</span>
                        </div>
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_employment_periods}</div>`;
        
        // Generate Student HTML
        const employeeStudentHTML = employee.is_student
            ? `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-header">
                        <h4 class="employee-profile__item-title">${window.EMPLOYEE_TRANSLATIONS.student}</h4>
                        ${employee.student_end_date ? `
                            <span class="employee-profile__item-status employee-profile__item-status--${isExpired(employee.student_end_date) ? 'expired' : 'valid'}">
                                ${isExpired(employee.student_end_date) ? window.EMPLOYEE_TRANSLATIONS.expired : window.EMPLOYEE_TRANSLATIONS.valid}
                            </span>
                        ` : ''}
                    </div>
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.status}</span>
                            <span class="employee-profile__field-value">${boolCast(employee.is_student) || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.end_date}</span>
                            <span class="employee-profile__field-value">${formatDate(employee.student_end_date) || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                    </div>
                </div>
            `
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_documents}</div>`;

        // Generate Documents HTML
        const documentsHTML = employee.documents?.length > 0
            ? employee.documents.map(doc => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-header">
                        <h4 class="employee-profile__item-title">${doc.document_type || window.EMPLOYEE_TRANSLATIONS.document}</h4>
                        ${doc.valid_until ? `
                            <span class="employee-profile__item-status employee-profile__item-status--${isExpired(doc.valid_until) ? 'expired' : 'valid'}">
                                ${isExpired(doc.valid_until) ? window.EMPLOYEE_TRANSLATIONS.expired : window.EMPLOYEE_TRANSLATIONS.valid}
                            </span>
                        ` : ''}
                    </div>
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.document_type}</span>
                            <span class="employee-profile__field-value">${doc.doc_type || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        ${doc.valid_until ? `
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.end_date}</span>
                                <span class="employee-profile__field-value">${formatDate(doc.valid_until)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_documents}</div>`;

        // Generate Work Permits HTML
        const workPermitsHTML = employee.work_permits?.length > 0
            ? employee.work_permits.map(permit => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-header">
                        <h4 class="employee-profile__item-title">${window.EMPLOYEE_TRANSLATIONS.work_permit}</h4>
                        <span class="employee-profile__item-status employee-profile__item-status--${isExpired(permit.end_date) ? 'expired' : 'valid'}">
                            ${isExpired(permit.end_date) ? window.EMPLOYEE_TRANSLATIONS.expired : window.EMPLOYEE_TRANSLATIONS.valid}
                        </span>
                    </div>
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.permit_type}</span>
                            <span class="employee-profile__field-value">${permit.doc_type || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.end_date}</span>
                            <span class="employee-profile__field-value">${formatDate(permit.end_date)}</span>
                        </div>
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_work_permits}</div>`;

        // Generate Card Submissions HTML
        const cardSubmissionsHTML = employee.card_submissions?.length > 0
            ? employee.card_submissions.map(card => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.application_type}</span>
                            <span class="employee-profile__field-value">${card.doc_type || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.submission_date}</span>
                            <span class="employee-profile__field-value">${formatDate(card.start_date)}</span>
                        </div>
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_card_submissions}</div>`;

        // Generate Contracts HTML
        const contractsHTML = employee.contracts?.length > 0
            ? employee.contracts.map(contract => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.contract_type}</span>
                            <span class="employee-profile__field-value">${contract.contract_type || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_contracts}</div>`;

        // Generate Sanepids HTML
        const sanepidsHTML = employee.sanepids?.length > 0
            ? employee.sanepids.map(sanepid => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-header">
                        <h4 class="employee-profile__item-title">${window.EMPLOYEE_TRANSLATIONS.sanitary_book}</h4>
                         ${sanepid.end_date ? `
                            <span class="employee-profile__item-status employee-profile__item-status--${isExpired(sanepid.end_date ) ? 'expired' : 'valid'}">
                                ${isExpired(sanepid.end_date ) ? window.EMPLOYEE_TRANSLATIONS.expired : window.EMPLOYEE_TRANSLATIONS.valid}
                            </span>
                        ` : ''}
                    </div>
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.status}</span>
                            <span class="employee-profile__field-value">${sanepid.doc_type || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.end_date}</span>
                            <span class="employee-profile__field-value">${formatDate(sanepid.end_date)}</span>
                        </div>
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_sanitary_books}</div>`;

        // Generate Contacts HTML
        const contactsHTML = employee.contacts?.length > 0
            ? employee.contacts.map(contact => `
                <div class="employee-profile__item">
                    <div class="employee-profile__item-grid">
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.contact_type}</span>
                            <span class="employee-profile__field-value">${contact.contact_type || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                        </div>
                        <div class="employee-profile__field">
                            <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.value}</span>
                            ${contact.contact_type?.toLowerCase() === 'email'
                ? `<a href="mailto:${contact.value}" class="employee-profile__field-value employee-profile__field-value--link">${contact.value}</a>`
                : contact.contact_type?.toLowerCase() === 'phone'
                    ? `<a href="tel:${contact.value}" class="employee-profile__field-value employee-profile__field-value--link">${contact.value}</a>`
                    : `<span class="employee-profile__field-value">${contact.value || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>`
            }
                        </div>
                    </div>
                </div>
            `).join('')
            : `<div class="employee-profile__empty">${window.EMPLOYEE_TRANSLATIONS.no_contacts}</div>`;

        // Build the complete profile card
        employeeCard.innerHTML = `
            <div class="employee-profile">
                <div class="employee-profile__header">
                    <div class="employee-profile__main-info">
                        <div class="employee-profile__avatar">
                         <svg fill="white" width="100" height="100" viewBox="0 0 60 60">
                            <path d="M60,30.017c0-16.542-13.458-30-30-30s-30,13.458-30,30c0,6.142,1.858,11.857,5.038,16.618l-0.002,0.018 c0.005,0,0.01,0.001,0.014,0.001c2.338,3.495,5.393,6.469,8.949,8.721c9.524,6.149,22.473,6.138,32,0 c2.599-1.646,4.928-3.677,6.907-6.017c0.001,0.001,0.002,0.002,0.002,0.003c0.023-0.027,0.045-0.057,0.068-0.084 c0.177-0.211,0.349-0.427,0.521-0.644c0.168-0.209,0.334-0.418,0.497-0.632c0.048-0.063,0.093-0.128,0.14-0.192 c0.21-0.281,0.422-0.56,0.621-0.851l0.207-0.303l-0.002-0.021C58.142,41.874,60,36.159,60,30.017z M58,30.017 c0,4.972-1.309,9.642-3.591,13.694c-1.647-5.46-6.563-9.373-12.409-9.662v-0.032h-0.689H36h-0.635c-0.201,0-0.365-0.164-0.365-0.365 v-0.645c0-0.183,0.149-0.303,0.276-0.352c6.439-2.421,10.455-12.464,9.613-19.488c-0.439-3.658-2.25-6.927-4.883-9.295 C50.517,7.909,58,18.103,58,30.017z M25.491,30.808C20.709,29.04,17,20.867,17,15.017c0-0.128,0.016-0.253,0.019-0.38l0.732-0.902 c1.651-1.964,4.47-2.526,7.012-1.4c1.022,0.453,2.111,0.683,3.237,0.683c2.971,0,5.64-1.615,7.028-4.184 c3.182,1.045,6.022,3.015,7.943,5.498c0.293,6.1-3.294,14.533-8.398,16.452C33.617,31.143,33,32.016,33,33.007v0.645 c0,1.304,1.062,2.365,2.365,2.365H36v6H24v-6h0.635c1.304,0,2.365-1.062,2.365-2.365v-0.635C27,32.031,26.395,31.143,25.491,30.808z M19.999,3.87C16.939,6.618,15,10.591,15,15.017c0,6.629,4.19,15.593,9.797,17.666C24.916,32.728,25,32.865,25,33.017v0.635 c0,0.201-0.164,0.365-0.365,0.365H24h-5.311H18v0.032c-5.846,0.289-10.762,4.202-12.409,9.662C3.309,39.659,2,34.989,2,30.017 C2,18.101,9.486,7.905,19.999,3.87z M7.544,46.724c0.003,0,0.006,0,0.009,0.001c-0.046-0.06-0.091-0.122-0.137-0.181 c-0.104-0.142-0.205-0.287-0.307-0.431C7.862,40.558,12.426,36.372,18,36.049v5.969h-4v10.958 C11.529,51.248,9.345,49.138,7.544,46.724z M46,52.976V42.017h-4v-5.969c5.574,0.323,10.138,4.51,10.891,10.064 c-0.073,0.104-0.146,0.207-0.221,0.31c-0.382,0.522-0.775,1.035-1.187,1.528C49.888,49.858,48.042,51.548,46,52.976z"/>
                        </svg>
                        </div>
                        <div class="employee-profile__name-block">
                            <h2 class="employee-profile__name">${fullName}</h2>
                            <p class="employee-profile__workplace">${window.EMPLOYEE_TRANSLATIONS.workplace}: ${employee.workplace || window.EMPLOYEE_TRANSLATIONS.workplace_not_specified}</p>
                            <div class="employee-profile__badges">
                                ${employee.is_student ? `<span class="employee-profile__badge employee-profile__badge--student">${window.EMPLOYEE_TRANSLATIONS.student}</span>` : ''}
                                <span class="employee-profile__badge employee-profile__badge--${activeMapper(employee.working_status)}">
                                    ${statusMapper(employee.working_status)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="employee-profile__content">
                    <!-- Personal Information -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.personal_information}
                        </h3>
                        <div class="employee-profile__grid">
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.first_name}</span>
                                <span class="employee-profile__field-value">${employee.first_name || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                            </div>
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.last_name}</span>
                                <span class="employee-profile__field-value">${employee.last_name || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                            </div>
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">${window.EMPLOYEE_TRANSLATIONS.age}</span>
                                <span class="employee-profile__field-value">${employee.age ? `${employee.age} ${window.EMPLOYEE_TRANSLATIONS.years}` : window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                            </div>
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">PESEL</span>
                                <span class="employee-profile__field-value">${employee.pesel || window.EMPLOYEE_TRANSLATIONS.not_specified}</span>
                            </div>
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">PESEL URK</span>
                                <span class="employee-profile__field-value">${employee.pesel_urk ? window.EMPLOYEE_TRANSLATIONS.yes : window.EMPLOYEE_TRANSLATIONS.no}</span>
                            </div>
                            <div class="employee-profile__field">
                                <span class="employee-profile__field-label">PIT-2</span>
                                <span class="employee-profile__field-value">${employee.pit_2 ? window.EMPLOYEE_TRANSLATIONS.yes : window.EMPLOYEE_TRANSLATIONS.no}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Student Condition -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.student}
                        </h3>
                        <div class="employee-profile__items">
                            ${employeeStudentHTML}
                        </div>
                    </div>

                    <!-- Employment Periods -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.employment_periods}
                        </h3>
                        <div class="employee-profile__items">
                            ${employmentPeriodsHTML}
                        </div>
                    </div>

                    <!-- Documents -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.documents}
                        </h3>
                        <div class="employee-profile__items">
                            ${documentsHTML}
                        </div>
                    </div>

                    <!-- Work Permits -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.work_permits}
                        </h3>
                        <div class="employee-profile__items">
                            ${workPermitsHTML}
                        </div>
                    </div>

                    <!-- Card Submissions -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
                                <path fill-rule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.card_submissions}
                        </h3>
                        <div class="employee-profile__items">
                            ${cardSubmissionsHTML}
                        </div>
                    </div>

                    <!-- Contracts -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.contracts}
                        </h3>
                        <div class="employee-profile__items">
                            ${contractsHTML}
                        </div>
                    </div>

                    <!-- Sanepids -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clip-rule="evenodd"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.sanitary_books}
                        </h3>
                        <div class="employee-profile__items">
                            ${sanepidsHTML}
                        </div>
                    </div>

                    <!-- Contacts -->
                    <div class="employee-profile__section">
                        <h3 class="employee-profile__section-title">
                            <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z"/>
                            </svg>
                            ${window.EMPLOYEE_TRANSLATIONS.contacts}
                        </h3>
                        <div class="employee-profile__items">
                            ${contactsHTML}
                        </div>
                    </div>

                    <!-- Additional Information -->
                    ${employee.additional_information ? `
                        <div class="employee-profile__section">
                            <h3 class="employee-profile__section-title">
                                <svg class="employee-profile__section-icon" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                                </svg>
                                ${window.EMPLOYEE_TRANSLATIONS.additional_information}
                            </h3>
                            <div class="employee-profile__additional-info">
                                ${employee.additional_information}
                            </div>
                        </div>
                    ` : ''}
                </div>

                <div class="employee-profile__actions">
                    <button class="employee-profile__btn employee-profile__btn--edit" onclick="editEmployeeFromCard(${employee.id})">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M12.146 1.146a.5.5 0 01.708 0l2 2a.5.5 0 010 .708l-9 9a.5.5 0 01-.168.11l-4 1.5a.5.5 0 01-.65-.65l1.5-4a.5.5 0 01.11-.168l9-9z"/>
                        </svg>
                        ${window.EMPLOYEE_TRANSLATIONS.edit}
                    </button>
                    <button class="employee-profile__btn employee-profile__btn--delete" onclick="deleteEmployeeFromCard(${employee.id})">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                            <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1z"/>
                        </svg>
                        ${window.EMPLOYEE_TRANSLATIONS.delete}
                    </button>
                </div>
            </div>
        `;

        viewEmployeeModal.classList.add('modal--active');
        document.body.style.overflow = 'hidden';

    } catch (error) {
        console.error('Error loading employee data:', error);
        showNotification(window.EMPLOYEE_TRANSLATIONS.error_loading_employee, 'error');
    }
}

// Close View Modal
function closeViewModal() {
    viewEmployeeModal.classList.remove('modal--active');
    document.body.style.overflow = '';
}

// Show Context Menu
function showContextMenu(event, employeeId) {
    currentEmployeeId = employeeId;

    const x = event.clientX;
    const y = event.clientY;

    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.classList.add('context-menu--active');

    // Adjust position if menu goes off screen
    setTimeout(() => {
        const rect = contextMenu.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            contextMenu.style.left = `${x - rect.width}px`;
        }
        if (rect.bottom > window.innerHeight) {
            contextMenu.style.top = `${y - rect.height}px`;
        }
    }, 0);
}

// Hide Context Menu
function hideContextMenu() {
    contextMenu.classList.remove('context-menu--active');
}

// Edit Employee from Card
function editEmployeeFromCard(employeeId) {
    closeViewModal();
    openModal('edit', employeeId);
}

// Delete Employee from Card
function deleteEmployeeFromCard(employeeId) {
    if (confirm(`${window.EMPLOYEE_TRANSLATIONS.delete_employee}`)) {
      deleteEmployee(employeeId);
      closeViewModal();
    }
}

// Delete Employee
async function deleteEmployee(employeeId) {
    try {
        const response = await fetch(`/api/auth/profile/${employeeId}/delete/`, {
            method: 'DELETE',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                showNotification(window.EMPLOYEE_TRANSLATIONS.auth_error_short, 'error');
                return;
            }
            if (response.status === 404) {
                showNotification(window.EMPLOYEE_TRANSLATIONS.employee_not_found, 'error');
                return;
            }
            throw new Error('Failed to delete employee');
        }

        // sessionStorage.setItem('notification', JSON.stringify({
        //     message: window.EMPLOYEE_TRANSLATIONS.employee_deleted,
        // }));
        // location.reload();

        // Перезавантажуємо таблицю через HTMX
        htmx.trigger('#employeesTable', 'htmx:load');
        showNotification(window.EMPLOYEE_TRANSLATIONS.employee_deleted);

    } catch (error) {
        console.error('Error deleting employee:', error);
        showNotification(window.EMPLOYEE_TRANSLATIONS.error_deleting_employee, 'error');
    }
}

// document.addEventListener('DOMContentLoaded', () => {
//     const notification = sessionStorage.getItem('notification');
//
//     if (notification) {
//         const {message, type} = JSON.parse(notification);
//         showNotification(message);
//         sessionStorage.removeItem('notification');
//     }
// });

// Add Employee Button
if (addEmployeeBtn) {
    addEmployeeBtn.addEventListener('click', openModal);
}

// Close Modal Events
modalClose.addEventListener('click', async () => await closeModal());
modalCancel.addEventListener('click', async () => await closeModal());
modalOverlay.addEventListener('click', async () => await closeModal());

// Close View Modal Events
viewModalClose.addEventListener('click', closeViewModal);
viewModalOverlay.addEventListener('click', closeViewModal);

// Context Menu Events
contextMenu.addEventListener('click', (e) => {
    const item = e.target.closest('.context-menu__item');
    if (!item) return;

    const action = item.dataset.action;

    switch (action) {
        case 'view':
            openViewModal(currentEmployeeId);
            break;
        case 'update':
            openModal('edit', currentEmployeeId);
            break;
        case 'delete':
            if (confirm(`${window.EMPLOYEE_TRANSLATIONS.delete_employee}`)) {
              deleteEmployee(currentEmployeeId);
            }
            break;
    }

    hideContextMenu();
});

// Hide context menu when clicking outside
document.addEventListener('click', (e) => {
    if (!contextMenu.contains(e.target) && !e.target.closest('.employees-table__menu-btn')) {
        hideContextMenu();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', async (e) => {
    if (e.key === 'Escape') {
        if (employeeModal.classList.contains('modal--active')) {
            await closeModal();
        }
        if (viewEmployeeModal.classList.contains('modal--active')) {
            closeViewModal();
        }
        if (contextMenu.classList.contains('context-menu--active')) {
            hideContextMenu();
        }
    }
});

function showNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #28A745;
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

// Add animation styles
const style = document.createElement('style');
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
`;
document.head.appendChild(style);

// Contact formset
document.addEventListener("DOMContentLoaded", () => {
    const addBtn = document.getElementById("add-contact");
    const list = document.getElementById("contacts-list");
    const template = document.querySelector("#contact-template .contacts__item");

    if (addBtn && list && template) {
        addBtn.addEventListener("click", () => {
            const formCount = document.querySelector('input[name$="-TOTAL_FORMS"]');

            if (!formCount) {
                console.error("TOTAL_FORMS not found!");
                return;
            }

            const current = parseInt(formCount.value, 10);

            // Clone the template instead of first child
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
});

// Filter functionality with HTMX
document.addEventListener('DOMContentLoaded', () => {
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

            htmx.ajax('GET', url.toString(), {
                target: '#employeesTable',
                swap: 'innerHTML',
                indicator: '#table-loading'
            });

            filterDropdownMenu.classList.remove('filter-dropdown__menu--active');
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
                target: '#employeesTable',
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

function clearSearch() {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.delete('q');

    const url = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');

    htmx.ajax('GET', url, {
        target: '#employeesTable',
        swap: 'innerHTML',
        indicator: '#table-loading'
    });
}


// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderEmployees();
});

// Re-initialize after HTMX swaps
document.body.addEventListener('htmx:afterSwap', () => {
    renderEmployees();
});


// PDF Export loading indicator
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
                
                // Скидаємо стан через 3 секунди (файл вже почав завантажуватись)
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
