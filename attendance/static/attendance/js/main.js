function fetchWithCsrf(url, options = {}) {
    // CSRF 토큰을 input[name=csrfmiddlewaretoken]에서 가져옴
    const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfTokenInput ? csrfTokenInput.value : (window.csrfToken || '');
    const defaultHeaders = {
        'X-CSRFToken': csrfToken,
        ...options.headers
    };
    // FormData가 아니면 Content-Type을 json으로
    if (!(options.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
    }
    return fetch(url, {
        ...options,
        headers: defaultHeaders
    });
}

$.ajaxSetup({
    headers: { "X-CSRFToken": csrfToken }
});

console.log('main.js 열려라 참깨 콩떡!');
console.log('print-preview-btn:', document.getElementById('print-preview-btn'));
console.log('close-pdf-modal-btn:', document.getElementById('close-pdf-modal-btn'));
console.log('print-pdf-btn:', document.getElementById('print-pdf-btn'));
console.log('download-pdf-btn:', document.getElementById('download-pdf-btn'));
console.log('download-excel-btn:', document.getElementById('download-excel-btn'));
console.log('pdf-iframe:', document.getElementById('pdf-iframe'));
console.log('pdf-preview-modal:', document.getElementById('pdf-preview-modal'));

document.addEventListener('DOMContentLoaded', () => {
    console.log("Attendance application JavaScript is fully loaded.");

    // ===================================================================
    //  ELEMENT SELECTORS
    // ===================================================================
    const monthDisplay = document.querySelector('.current-month');
    const dailyEntryTitle = document.getElementById('daily-entry-title');
    const techaveLogo = document.getElementById('techave-logo');
    
    // Modal
    const monthlyModal = document.getElementById('monthly-modal');
    const createMonthlyBtn = document.getElementById('create-monthly-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const monthlyForm = document.getElementById('monthly-form');

    // Navigation
    const prevMonthBtn = document.getElementById('prev-month-btn');
    const nextMonthBtn = document.getElementById('next-month-btn');

    // Excel Download
    const excelDownloadBtn = document.getElementById('excel-download-btn');

    // Daily Form
    const dailyForm = document.getElementById('daily-entry-form');
    const calendarTable = document.querySelector('.calendar-table');
    const dayDisplay = document.getElementById('day-display');
    const dayInputHidden = document.getElementById('day-input-hidden');
    const getDailyDataUrl = '/daily/get/';

    // New elements for Year/Month Picker
    const pickerModal = document.getElementById('year-month-picker-modal');
    const closePickerBtn = document.getElementById('close-picker-btn');
    const pickerYearDisplay = document.getElementById('picker-year');
    const prevYearBtn = document.getElementById('prev-year-btn');
    const nextYearBtn = document.getElementById('next-year-btn');
    const monthGrid = document.querySelector('.month-grid');

    let currentYear, currentMonth;

    // ===================== メール送信ロジック =====================
    const emailForm = document.getElementById('email-send-form');
    const emailInput = document.getElementById('email-to');
    const emailHostUserInput = document.getElementById('email-host-user');
    const emailHostPasswordInput = document.getElementById('email-host-password');
    const emailStatus = document.getElementById('email-status-message');
    const fileTypeModal = document.getElementById('file-type-modal');
    const closeFileTypeModalBtn = document.getElementById('close-file-type-modal-btn');
    const sendPdfBtn = document.getElementById('send-pdf-btn');
    const sendExcelBtn = document.getElementById('send-excel-btn');

    let pendingEmail = '';
    let pendingHostUser = '';
    let pendingHostPassword = '';

    if (emailForm && emailInput && fileTypeModal) {
        emailForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = emailInput.value.trim();
            const hostUser = emailHostUserInput ? emailHostUserInput.value.trim() : '';
            const hostPassword = emailHostPasswordInput ? emailHostPasswordInput.value.trim() : '';
            
            if (!email) return;
            pendingEmail = email;
            pendingHostUser = hostUser;
            pendingHostPassword = hostPassword;
            // 파일 종류 선택 모달 표시
            fileTypeModal.style.display = 'flex';
        });
    }
    if (closeFileTypeModalBtn && fileTypeModal) {
        closeFileTypeModalBtn.addEventListener('click', function() {
            fileTypeModal.style.display = 'none';
        });
    }
    function showEmailStatus(msg, isError=false) {
        if (emailStatus) {
            emailStatus.textContent = msg;
            emailStatus.style.display = 'block';
            emailStatus.style.color = isError ? '#dc3545' : '#007bff';
            setTimeout(() => { emailStatus.style.display = 'none'; }, 4000);
        }
    }
    async function sendMailRequest(fileType) {
        if (!pendingEmail) return;
        // 현재 년/월 정보
        const year = document.getElementById('current-month-display').dataset.year;
        const month = document.getElementById('current-month-display').dataset.month;
        showEmailStatus('送信中...', false);
        try {
            const response = await fetch('/attendance/email/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    email: pendingEmail,
                    file_type: fileType,
                    year: year,
                    month: month,
                    email_host_user: pendingHostUser,
                    email_host_password: pendingHostPassword
                })
            });
            const result = await response.json();
            if (result.status === 'success') {
                showEmailStatus('メールが正常に送信されました！', false);
            } else {
                showEmailStatus(result.message || '送信に失敗しました。', true);
            }
        } catch (err) {
            showEmailStatus('送信中にエラーが発生しました。', true);
        }
        fileTypeModal.style.display = 'none';
        pendingEmail = '';
        pendingHostUser = '';
        pendingHostPassword = '';
    }
    if (sendPdfBtn) {
        sendPdfBtn.addEventListener('click', function() {
            sendMailRequest('pdf');
        });
    }
    if (sendExcelBtn) {
        sendExcelBtn.addEventListener('click', function() {
            sendMailRequest('excel');
        });
    }

    // ===================================================================
    //  UTILITY FUNCTIONS
    // ===================================================================
    
    /**
     * 年月ピッカーを生成・更新
     * @param {number} year - 表示する年
     */
    function updateYearMonthPicker(year) {
        pickerYearDisplay.textContent = year;
        monthGrid.innerHTML = '';
        for (let i = 1; i <= 12; i++) {
            const monthBtn = document.createElement('button');
            monthBtn.textContent = `${i}月`;
            monthBtn.dataset.month = i;
            monthGrid.appendChild(monthBtn);
        }
    }

    /**
     * カレンダーやリストを特定の年月に更新
     * @param {number} year 
     * @param {number} month 
     */
    function navigate(year, month, day) {
        let url = `?year=${year}&month=${month}`;
        if (day) url += `&day=${day}`;
        window.location.href = url;
    }

    /**
     * 日別勤怠データをフォームに表示
     * @param {string} date - 'YYYY-MM-DD'形式の日付
     */
    async function populateDailyForm(date) {
        // 選択されたセルのハイライトを更新
        const selectedCell = document.querySelector('.calendar-table td.selected');
        if (selectedCell) {
            selectedCell.classList.remove('selected');
        }
        const newSelectedCell = document.querySelector(`.calendar-table td[data-date='${date}']`);
        if (newSelectedCell) {
            newSelectedCell.classList.add('selected');
        }

        try {
            const response = await fetchWithCsrf(`/daily/get/?date=${date}`);
            if (!response.ok) {
                throw new Error('日次データの取得に失敗しました。');
            }
            const data = await response.json();
            
            const form = document.getElementById('daily-entry-form');
            
            // 日付から日(day)を抽出して設定
            const dateObj = new Date(date);
            const day = dateObj.getDate();
            
            if (dayInputHidden) {
                dayInputHidden.value = day;
            }
            
            // フォームタイトルを更新
            if (dailyEntryTitle) {
                dailyEntryTitle.textContent = `勤怠登録 `;          //(${dateObj.getMonth() + 1}/${day})
            }

            if (data.record) {
                // 既存データがある場合
                form.querySelector('[name="work_type"]').value = data.record.work_type || '';
                form.querySelector('[name="alternative_work_date"]').value = data.record.alternative_work_date || '';
                form.querySelector('[name="start_time"]').value = data.record.start_time || '';
                form.querySelector('[name="end_time"]').value = data.record.end_time || '';
                form.querySelector('[name="notes"]').value = data.record.notes || '';
            } else {
                // 新規データの場合
                form.reset();
                if (dayInputHidden) {
                    dayInputHidden.value = day;
                }
                // 勤務区分のデフォルト値を設定
                const workTypeSelect = form.querySelector('[name="work_type"]');
                if (workTypeSelect) {
                    workTypeSelect.value = '出勤';
                }
                // その他のフィールドをクリア
                form.querySelector('[name="alternative_work_date"]').value = '';
                form.querySelector('[name="start_time"]').value = '';
                form.querySelector('[name="end_time"]').value = '';
                form.querySelector('[name="notes"]').value = '';
            }
            // 승인/대기/완료 상태에 따라 폼 비활성화
            handleDailyFormLock(data.record);

            // ★ 폼 값 채운 후 원본값 저장!
            saveOriginalFormData();
        } catch (error) {
            console.error('Populate form error:', error);
            alert('フォームのデータ取得中にエラーが発生しました。');
        }
    }

    // ===================================================================
    //  MONTHLY MODAL CONTROL
    // ===================================================================
    if (monthlyModal) {
        if (createMonthlyBtn) {
            createMonthlyBtn.addEventListener('click', () => {
                monthlyModal.style.display = 'flex';
            });
        }
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => {
                monthlyModal.style.display = 'none';
            });
        }
        monthlyModal.addEventListener('click', (e) => {
            if (e.target === monthlyModal) {
                monthlyModal.style.display = 'none';
            }
        });
    }

    // ===================================================================
    //  MONTH NAVIGATION
    // ===================================================================
    const urlParams = new URLSearchParams(window.location.search);
    let initialYear = parseInt(urlParams.get('year')) || new Date().getFullYear();
    let initialMonth = parseInt(urlParams.get('month')) || new Date().getMonth() + 1;
    
    currentYear = initialYear;
    currentMonth = initialMonth;

    // Techave 로고 클릭 시 현재 월로 돌아오는
    if (techaveLogo) {
        techaveLogo.addEventListener('click', () => {
            const today = new Date();
            const currentYear = today.getFullYear();
            const currentMonth = today.getMonth() + 1;
            navigate(currentYear, currentMonth, today.getDate());
        });
    }

    // 月移動ボタン의 이벤트리스너
    if (prevMonthBtn) {
        console.log('Previous month button found');
        prevMonthBtn.addEventListener('click', () => {
            console.log('Previous month clicked');
            let newMonth = currentMonth - 1;
            let newYear = currentYear;
            if (newMonth < 1) {
                newMonth = 12;
                newYear--;
            }
            navigate(newYear, newMonth);
        });
    }

    if (nextMonthBtn) {
        console.log('Next month button found');
        nextMonthBtn.addEventListener('click', () => {
            console.log('Next month clicked');
            let newMonth = currentMonth + 1;
            let newYear = currentYear;
            if (newMonth > 12) {
                newMonth = 1;
                newYear++;
            }
            navigate(newYear, newMonth);
        });
    }

    // ===================================================================
    //  MONTHLY FORM SUBMISSION (AJAX)
    // ===================================================================
    if (monthlyForm) {
        monthlyForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Monthly form submission started');
            
            const formData = new FormData(this);
            const actionUrl = this.action;
            
            if(monthDisplay) {
                formData.append('year', monthDisplay.dataset.year);
                formData.append('month', monthDisplay.dataset.month);
            }
            
            console.log('Monthly form data:', Object.fromEntries(formData.entries()));

            try {
                console.log('Sending monthly request to:', actionUrl);
                const response = await fetchWithCsrf(actionUrl, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData,
                });
                
                console.log('Monthly response status:', response.status);
                console.log('Monthly response ok:', response.ok);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.log('Monthly error response text:', errorText);
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('Monthly response data:', data);
                
                if (data.status === 'success') {
                    window.location.reload();
                } else {
                    let error_message = "登録に失敗しました。\n" + (data.message || '');
                    if(data.errors) {
                        for(const field in data.errors) {
                            error_message += `\n- ${data.errors[field][0].message || data.errors[field]}`;
                        }
                    }
                    showFormWarning(error_message);
                }
            } catch (error) {
                console.error('Error submitting monthly data:', error);
                console.error('Monthly error details:', {
                    name: error.name,
                    message: error.message,
                    stack: error.stack
                });
                // 서버에러라도 실제로는 등록되어있을 가능성이 있으므로, 확인메시지 표시
                if (confirm('서버와의 통신중에 에러가 발생했지만, 데이터는 정상적으로 등록되어있을 가능성이 있습니다.\n\n페이지를 다시 읽어들리겠습니까？')) {
                    window.location.reload();
                }
            }
        });
    }

    // ===================================================================
    //  CALENDAR INTERACTIONS
    // ===================================================================
    if (calendarTable) {
        calendarTable.addEventListener('click', (e) => {
            const cell = e.target.closest('td');
            if (cell && !cell.classList.contains('other-month')) {
                const date = cell.dataset.date;
                if (date) {
                    hideFormWarning();
                    const dateObj = new Date(date);
                    const day = dateObj.getDate();
                    updateDayDisplay(day);
                    populateDailyForm(date);
                }
            }
        });
    }

    // ===================================================================
    //  MANUAL DATE INPUT
    // ===================================================================
    if (dayInputHidden) {
        dayInputHidden.addEventListener('change', (e) => {
            const selectedDay = e.target.value;
            if (selectedDay && currentYear && currentMonth) {
                const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(selectedDay).padStart(2, '0')}`;
                populateDailyForm(dateStr);
            }
        });
    }

    // ===================================================================
    //  DAILY FORM SUBMISSION
    // ===================================================================
    if (dailyForm) {
        dailyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('Daily form submission started');
            
            const form = e.target;
            
            // 필수 필드 검증
            const workType = form.querySelector('select[name="work_type"]').value;
            const startTime = form.querySelector('input[name="start_time"]').value;
            const endTime = form.querySelector('input[name="end_time"]').value;
            
            if (!workType) {
                alert('勤務区分を選択してください。');
                form.querySelector('select[name="work_type"]').focus();
                return;
            }
            
            if (!startTime) {
                alert('作業開始時刻を入力してください。');
                form.querySelector('input[name="start_time"]').focus();
                return;
            }
            
            if (!endTime) {
                alert('作業終了時刻を入力してください。');
                form.querySelector('input[name="end_time"]').focus();
                return;
            }
            
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            
            // 현재의 년월정보를 추가
            data.year = currentYear;
            data.month = currentMonth;
            
            console.log('Form data to be sent:', data);
        
            try {
                console.log('Sending request to /daily/update/');
                const response = await fetchWithCsrf('/daily/update/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                
                console.log('Response status:', response.status);
                console.log('Response ok:', response.ok);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.log('Error response text:', errorText);
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
        
                const result = await response.json();
                console.log('Response data:', result);
        
                if (result.status === 'success') {
                    // 페이지를 리로드하여 캘린더표시를 업데이트
                    window.location.reload();
                } else {
                    let errorMessage = '에러가 발생했습니다。';
                    if (result.errors) {
                        errorMessage = Object.values(result.errors).flat().join('\n');
                    } else if (result.message) {
                        errorMessage = result.message;
                    }
                    showFormWarning(errorMessage);
                    restoreOriginalFormData();
                }
            } catch (error) {
                console.error('Error submitting daily data:', error);
                console.error('Error details:', {
                    name: error.name,
                    message: error.message,
                    stack: error.stack
                });
                // 서버에러라도 실제로는 등록되어있을 가능성이 있으므로, 확인메시지 표시
                if (confirm('서버와의 통신중에 에러가 발생했지만, 데이터는 정상적으로 등록되어있을 가능성이 있습니다.\n\n페이지를 다시 읽어들리겠습니까？')) {
                    window.location.reload();
                }
            }
        });
    }

    // ===================================================================
    //  YEAR/MONTH PICKER EVENTS
    // ===================================================================
    if (monthDisplay && pickerModal) {
        console.log('Month display and picker modal found');
        monthDisplay.addEventListener('click', () => {
            console.log('Month display clicked');
            updateYearMonthPicker(currentYear);
            pickerModal.style.display = 'flex';
        });
    }

    if (closePickerBtn) {
        closePickerBtn.addEventListener('click', () => {
            pickerModal.style.display = 'none';
        });
    }

    if (prevYearBtn) {
        prevYearBtn.addEventListener('click', () => {
            currentYear--;
            updateYearMonthPicker(currentYear);
        });
    }

    if (nextYearBtn) {
        nextYearBtn.addEventListener('click', () => {
            currentYear++;
            updateYearMonthPicker(currentYear);
        });
    }

    if (monthGrid) {
        monthGrid.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const selectedMonth = e.target.dataset.month;
                navigate(currentYear, parseInt(selectedMonth));
                pickerModal.style.display = 'none';
            }
        });
    }

    // 모달의 외측클릭으로 닫기
    if (pickerModal) {
        pickerModal.addEventListener('click', (e) => {
            if (e.target === pickerModal) {
                pickerModal.style.display = 'none';
            }
        });
    }

    // ===================================================================
    //  DELETE FUNCTIONALITY
    // ===================================================================

    // 일별정보삭제
    document.addEventListener('click', async (e) => {
        if (e.target.closest('.delete-daily-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const deleteBtn = e.target.closest('.delete-daily-btn');
            const date = deleteBtn.dataset.date;
            
            if (confirm('この日付の勤務情報を本当に削除しますか？')) {
                try {
                    console.log('Deleting daily attendance for date:', date);
                    const response = await fetchWithCsrf('/daily/delete/', {
                        method: 'POST',
                        body: JSON.stringify({
                            date: date
                        })
                    });
                    
                    console.log('Delete daily response status:', response.status);
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        console.log('Delete daily error response text:', errorText);
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const result = await response.json();
                    console.log('Delete daily response data:', result);
                    
                    if (result.status === 'success') {
                        alert(result.message);
                        window.location.reload();
                    } else {
                        alert('エーラ: ' + (result.message || '削除に失敗しました。'));
                    }
                } catch (error) {
                    console.error('Error deleting daily data:', error);
                    alert('削除の中にエーラが発生しました。: ' + error.message);
                }
            }
        }
    });

    // ===================================================================
    //  NORMAL HOURS BUTTON
    // ===================================================================
    const normalHoursBtn = document.getElementById('normal-hours-btn');
    if (normalHoursBtn) {
        normalHoursBtn.addEventListener('click', () => {
            const startTimeInput = document.querySelector('[name="start_time"]');
            const endTimeInput = document.querySelector('[name="end_time"]');
            
            // 월별 데이터의 기준 캘린더 확인
            const baseCalendar = normalHoursBtn.dataset.baseCalendar;
            
            if (baseCalendar === 'H大甕') {
                // H大甕 캘린더: 8:40 - 17:10
                if (startTimeInput) {
                    startTimeInput.value = '08:40';
                }
                if (endTimeInput) {
                    endTimeInput.value = '17:10';
                }
                console.log('Normal hours set (H大甕): 08:40 - 17:10');
            } else {
                // 기준 캘린더: 9:00 - 18:00
                if (startTimeInput) {
                    startTimeInput.value = '09:00';
                }
                if (endTimeInput) {
                    endTimeInput.value = '18:00';
                }
                console.log('Normal hours set (基準): 09:00 - 18:00');
            }
        });
    }

    // ===================================================================
    //  MONTHLY UPDATE MODAL CONTROL
    // ===================================================================
    const monthlyUpdateModal = document.getElementById('monthly-update-modal');
    const editMonthlyBtn = document.getElementById('edit-monthly-btn');
    const closeUpdateModalBtn = document.getElementById('close-update-modal-btn');
    const monthlyUpdateForm = document.getElementById('monthly-update-form');

    if (monthlyUpdateModal) {
        if (editMonthlyBtn) {
            editMonthlyBtn.addEventListener('click', () => {
                // 현재의 월별정보를 폼에 설정
                const projectNameInput = document.getElementById('update-project-name');
                const baseCalendarInput = document.getElementById('update-base-calendar');
                const lunchBreakInput = document.getElementById('update-lunch-break');
                const standardTimeInput = document.getElementById('update-standard-time');
                
                // 월별정보의 값을 가져오기 (템플릿에서)
                const lunchBreakRaw = document.querySelectorAll('.detail-item strong')[2].textContent;
                const lunchBreakValue = lunchBreakRaw.replace(/[^0-9.]/g, ''); // 숫자만 추출

                const standardTimeRaw = document.querySelectorAll('.detail-item strong')[3].textContent;
                const standardTimeValue = standardTimeRaw.replace(/[^0-9.]/g, ''); // 숫자만 추출
                
                if (projectNameInput) projectNameInput.value = document.querySelector('.detail-item strong').textContent;
                if (baseCalendarInput) baseCalendarInput.value = document.querySelectorAll('.detail-item strong')[1].textContent;
                if (lunchBreakInput) lunchBreakInput.value = lunchBreakValue;
                if (standardTimeInput) standardTimeInput.value = standardTimeValue;
                
                monthlyUpdateModal.style.display = 'flex';
            });
        }
        
        if (closeUpdateModalBtn) {
            closeUpdateModalBtn.addEventListener('click', () => {
                monthlyUpdateModal.style.display = 'none';
            });
        }
        
        monthlyUpdateModal.addEventListener('click', (e) => {
            if (e.target === monthlyUpdateModal) {
                monthlyUpdateModal.style.display = 'none';
            }
        });
    }

    // ===================================================================
    //  MONTHLY UPDATE FORM SUBMISSION
    // ===================================================================
    if (monthlyUpdateForm) {
        monthlyUpdateForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Monthly update form submission started');
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());
            
            // 현재의 년월정보를 추가
            data.year = currentYear;
            data.month = currentMonth;
            
            console.log('Monthly update form data:', data);

            try {
                console.log('Sending monthly update request to: /monthly/update/');
                const response = await fetchWithCsrf('/monthly/update/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                
                console.log('Monthly update response status:', response.status);
                console.log('Monthly update response ok:', response.ok);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.log('Monthly update error response text:', errorText);
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                console.log('Monthly update response data:', result);
                
                if (result.status === 'success') {
                    monthlyUpdateModal.style.display = 'none';
                    window.location.reload();
                } else {
                    let errorMessage = '에러가 발생했습니다。';
                    if (result.errors) {
                        errorMessage = Object.values(result.errors).flat().join('\n');
                    } else if (result.message) {
                        errorMessage = result.message;
                    }
                    showFormWarning(errorMessage);
                }
            } catch (error) {
                console.error('Error updating monthly data:', error);
                console.error('Monthly update error details:', {
                    name: error.name,
                    message: error.message,
                    stack: error.stack
                });
                alert('수정중에 에러가 발생했습니다: ' + error.message);
            }
        });
    }

    // ===================================================================
    //  ADD MONTHLY BUTTON
    // ===================================================================
    const addMonthlyBtn = document.getElementById('add-monthly-btn');
    if (addMonthlyBtn) {
        addMonthlyBtn.addEventListener('click', () => {
            const monthlyModal = document.getElementById('monthly-modal');
            if (monthlyModal) {
                monthlyModal.style.display = 'flex';
            }
        });
    }

    // ===================================================================
    //  EXCEL DOWNLOAD BUTTON
    // ===================================================================
    if (excelDownloadBtn) {
        excelDownloadBtn.addEventListener('click', async () => {
            try {
                console.log('Excel download requested for:', currentYear, currentMonth);
                
                // 현재의 년월로 엑셀다운로드URL을 구성
                const downloadUrl = `/excel/download/?year=${currentYear}&month=${currentMonth}`;
                
                // 새로운 창으로 다운로드를 시작
                window.open(downloadUrl, '_blank');
                
            } catch (error) {
                console.error('Error downloading Excel file:', error);
                alert('엑셀파일의 다운로드중에 에러가 발생했습니다: ' + error.message);
            }
        });
    }

    // Print Preview Button (메인 버튼)
    const printPreviewBtn = document.getElementById('print-preview-btn');
    if (printPreviewBtn) {
        printPreviewBtn.addEventListener('click', function() {
            const year = document.getElementById('current-month-display').dataset.year;
            const month = document.getElementById('current-month-display').dataset.month;
            const pdfUrl = `/pdf/preview/?year=${year}&month=${month}`;

            // PDF iframe에 URL 설정
            const pdfIframe = document.getElementById('pdf-iframe');
            if (pdfIframe) pdfIframe.src = pdfUrl;

            // 모달 표시
            const pdfModal = document.getElementById('pdf-preview-modal');
            if (pdfModal) pdfModal.style.display = 'flex';
        });
    }

    // Close PDF Modal
    const closePdfModalBtn = document.getElementById('close-pdf-modal-btn');
    if (closePdfModalBtn) {
        closePdfModalBtn.addEventListener('click', function() {
            const pdfModal = document.getElementById('pdf-preview-modal');
            if (pdfModal) pdfModal.style.display = 'none';
            const pdfIframe = document.getElementById('pdf-iframe');
            if (pdfIframe) pdfIframe.src = '';
        });
    }

    // Print PDF Button
    const printPdfBtn = document.getElementById('print-pdf-btn');
    if (printPdfBtn) {
        printPdfBtn.addEventListener('click', function() {
            const iframe = document.getElementById('pdf-iframe');
            if (iframe && iframe.contentWindow) iframe.contentWindow.print();
        });
    }

    // Download PDF Button
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', function() {
            const year = document.getElementById('current-month-display').dataset.year;
            const month = document.getElementById('current-month-display').dataset.month;
            const pdfUrl = `/pdf/preview/?year=${year}&month=${month}`;
            const link = document.createElement('a');
            link.href = pdfUrl;
            // 일본어 + 사원명 포함
            link.download = `${year}_${month}_稼動報告書_.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    // Download Excel Button
    const downloadExcelBtn = document.getElementById('download-excel-btn');
    if (downloadExcelBtn) {
        downloadExcelBtn.addEventListener('click', function() {
            const year = document.getElementById('current-month-display').dataset.year;
            const month = document.getElementById('current-month-display').dataset.month;
            const excelUrl = `/excel/download/?year=${year}&month=${month}`;
            const link = document.createElement('a');
            link.href = excelUrl;
            // 일본어 + 사원명 포함
            link.download = `${year}_${month}_稼動報告書_.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    // ===================== 탭 전환 로직 =====================
    // 탭 전환
    const tabCalendarBtn = document.getElementById('tab-calendar');
    const tabListBtn = document.getElementById('tab-list');
    const calendarTab = document.getElementById('calendar-tab');
    const listTab = document.getElementById('list-tab');

    console.log('tabCalendarBtn:', tabCalendarBtn);
    console.log('tabListBtn:', tabListBtn);
    console.log('calendarTab:', calendarTab);
    console.log('listTab:', listTab);

    if (tabCalendarBtn && tabListBtn && calendarTab && listTab) {
        tabCalendarBtn.addEventListener('click', function() {
            tabCalendarBtn.classList.add('active');
            tabListBtn.classList.remove('active');
            calendarTab.style.display = '';
            listTab.style.display = 'none';
            // 탭 상태 저장
            localStorage.setItem('selectedTab', 'calendar');
        });
        tabListBtn.addEventListener('click', function() {
            tabListBtn.classList.add('active');
            tabCalendarBtn.classList.remove('active');
            calendarTab.style.display = 'none';
            listTab.style.display = '';
            // 탭 상태 저장
            localStorage.setItem('selectedTab', 'list');
        });
    }

    // ===================== 공휴일(일본 API + DB holidays_db) 통합 표시 =====================
    /**
     * 일본 공휴일 API에서 이번 달 데이터만 추출하여 캘린더에 표시
     */
    async function applyApiHolidaysToCalendar() {
        const url = 'https://holidays-jp.github.io/api/v1/date.json';
        let apiHolidays = {};
        try {
            const res = await fetch(url);
            apiHolidays = await res.json();
        } catch (e) {
            console.error('API 공휴일 fetch 오류:', e);
            return;
        }
        const year = currentYear || (new Date()).getFullYear();
        const month = currentMonth || (new Date()).getMonth() + 1;
        const monthStr = String(month).padStart(2, '0');
        Object.entries(apiHolidays).forEach(([date, name]) => {
            if (date.startsWith(`${year}-${monthStr}`)) {
                const td = document.querySelector(`.calendar-table td[data-date='${date}']`);
                if (td) {
                    appendHolidayToCell(td, name, 'api');
                }
            }
        });
        console.log('API 공휴일 적용 완료:', year, month, apiHolidays);
    }

    /**
     * DB holidays_db에서 共通/개별(base_calendar) 구분하여 캘린더에 표시
     */
    function applyDbHolidaysToCalendar() {
        let holidaysDb = {};
        try {
            const holidaysScript = document.getElementById('holidays-db-data');
            if (holidaysScript) {
                holidaysDb = JSON.parse(holidaysScript.textContent);
            }
        } catch (e) {
           console.error('holidays_db 파싱 오류:', e);
        }
        const tds = document.querySelectorAll('.calendar-table td[data-date]');
        tds.forEach(td => {
            const dateStr = td.getAttribute('data-date');
            const dateNumDiv = td.querySelector('.date-number');
            if (!dateNumDiv) return;
            // 기존 DB holiday 표시 초기화
            dateNumDiv.querySelectorAll('.holiday-db-common-name, .holiday-db-base-name, .holiday-db-green-name').forEach(e => e.remove());
            if (holidaysDb[dateStr]) {
                holidaysDb[dateStr].forEach(h => {
                    let className = 'db';
                    if (h.calendar_name === '共通') className += ' common';
                    else if (h.category && h.category.includes('年休収得')) className += ' green';
                    else className += ' base';
                    appendHolidayToCell(td, h.category, className);
                });
            }
        });
        console.log('DB holidays_db 적용 완료:', holidaysDb);
    }

    function appendHolidayToCell(td, text, className) {
        let holidayCategory = td.querySelector('.holiday-category');
        if (!holidayCategory) {
            // 없으면 생성해서 .cell-header에 append
            const cellHeader = td.querySelector('.cell-header');
            if (!cellHeader) return;
            holidayCategory = document.createElement('span');
            holidayCategory.className = 'holiday-category';
            cellHeader.appendChild(holidayCategory);
        }
        const span = document.createElement('span');
        span.className = 'holiday-cat-item ' + className;
        span.textContent = text;
        holidayCategory.appendChild(span);

        // 숫자(span.date-number)에 holiday 클래스 추가 (빨간색)
        const dateNumber = td.querySelector('.date-number');
        if (dateNumber && !dateNumber.classList.contains('holiday')) {
            dateNumber.classList.add('holiday');
        }
    }

    /**
     * 모든 공휴일 표시(초기화 포함)
     */
    async function applyAllHolidaysToCalendar() {
        // 1. 기존 표시 초기화 (API/DB 모두)
        const tds = document.querySelectorAll('.calendar-table td[data-date]');
        tds.forEach(td => {
            const dateNumDiv = td.querySelector('.date-number');
            if (dateNumDiv) {
                dateNumDiv.querySelectorAll('.holiday-api-name, .holiday-db-common-name, .holiday-db-base-name').forEach(e => e.remove());
            }
        });
        // 2. API → 3. DB 순서로 적용
        await applyApiHolidaysToCalendar();
        applyDbHolidaysToCalendar();
    }

    // DOMContentLoaded 시점에 모두 적용
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyAllHolidaysToCalendar);
    } else {
        applyAllHolidaysToCalendar();
    }

    // ===================== 月情報セクション全体開閉トグル（上部単独ボタン） =====================
    const monthlyInfoSection = document.getElementById('monthly-info-section');
    const showMonthlyInfoBtn = document.getElementById('show-monthly-info-btn');
    const hideMonthlyInfoBtn = document.getElementById('hide-monthly-info-btn');

    if (monthlyInfoSection && showMonthlyInfoBtn && hideMonthlyInfoBtn) {
        // 初期状態: section非表示, +ボタン만 표시
        monthlyInfoSection.style.display = 'none';
        showMonthlyInfoBtn.style.display = 'inline';
        hideMonthlyInfoBtn.style.display = 'none';

        // monthly-info 섹션 열기
        showMonthlyInfoBtn.addEventListener('click', function() {
            monthlyInfoSection.style.display = '';
            showMonthlyInfoBtn.style.display = 'none';
            hideMonthlyInfoBtn.style.display = 'inline';
            // 상태 저장
            localStorage.setItem('monthlyInfoOpen', '1');
        });
        // monthly-info 섹션 닫기
        hideMonthlyInfoBtn.addEventListener('click', function() {
            monthlyInfoSection.style.display = 'none';
            showMonthlyInfoBtn.style.display = 'inline';
            hideMonthlyInfoBtn.style.display = 'none';
            // 상태 저장
            localStorage.setItem('monthlyInfoOpen', '0');
        });
    }
    
    // 생성 폼
    $(document).on('change', '#create-base-calendar', function() {
        console.log('바뀜');
        if ($(this).val() === 'H大甕') {
            $('#create-lunch-break').val('45');
            $('#create-standard-time').val('7.75');
        } else {
            $('#create-lunch-break').val('60');
            $('#create-standard-time').val('8.00');
        }
    });
    
    // 수정 폼
    $(document).on('change', '#update-base-calendar', function() {
        console.log('바뀜');
        if ($(this).val() === 'H大甕') {
           $('#update-lunch-break').val('45');
           $('#update-standard-time').val('7.75');
       } else {
           $('#update-lunch-break').val('60');
           $('#update-standard-time').val('8.00');
       }
    });
    
    // 昼休み区分과 基準時間 필드를 완전히 비활성화
    $(document).on('DOMContentLoaded', function() {
        // 생성 폼 필드 비활성화
        $('#create-lunch-break').prop('disabled', true);
        $('#create-standard-time').prop('disabled', true);
        
        // 수정 폼 필드 비활성화
        $('#update-lunch-break').prop('disabled', true);
        $('#update-standard-time').prop('disabled', true);
    });
    
    // 사용자가 직접 수정하려고 할 때 방지
    $(document).on('input change keydown', '#create-lunch-break, #create-standard-time, #update-lunch-break, #update-standard-time', function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    });

    // ===================== 日付 화살표 제어 및 UX/UI 개선 =====================
    const dayArrowLeft = document.getElementById('day-arrow-left');
    const dayArrowRight = document.getElementById('day-arrow-right');

    function getLastDayOfMonth(year, month) {
        return new Date(year, month, 0).getDate();
    }

    function setDayInputMinMax() {
        if (dayInputHidden) {
            const lastDay = getLastDayOfMonth(currentYear, currentMonth);
            dayInputHidden.min = 1;
            dayInputHidden.max = lastDay;
        }
    }
    setDayInputMinMax();

    // day-input 값이 비정상(범위 밖)이면 자동 보정 및 빨간 테두리 표시
    if (dayInputHidden) {
        dayInputHidden.addEventListener('input', function() {
            const val = parseInt(dayInputHidden.value, 10);
            const min = parseInt(dayInputHidden.min, 10);
            const max = parseInt(dayInputHidden.max, 10);
            if (isNaN(val) || val < min || val > max) {
                dayInputHidden.classList.add('input-error');
            } else {
                dayInputHidden.classList.remove('input-error');
            }
        });
        dayInputHidden.addEventListener('blur', function() {
            let val = parseInt(dayInputHidden.value, 10);
            const min = parseInt(dayInputHidden.min, 10);
            const max = parseInt(dayInputHidden.max, 10);
            if (isNaN(val) || val < min) val = min;
            if (val > max) val = max;
            dayInputHidden.value = val;
            dayInputHidden.classList.remove('input-error');
        });
    }

    // 화살표 hover 효과
    const style = document.createElement('style');
    style.innerHTML = ` 
        .input-error { border: 2px solid #e53935 !important; }
        .btn-today:hover { background: #bbdefb; }
    `;
    document.head.appendChild(style);

    function moveDay(delta) {
        if (!dayDisplay || !dayInputHidden) return;
        let day = parseInt(dayInputHidden.value, 10) || 1;
        const lastDay = getLastDayOfMonth(currentYear, currentMonth);
        day += delta;
        if (day < 1) {
            let newMonth = currentMonth - 1;
            let newYear = currentYear;
            if (newMonth < 1) {
                newMonth = 12;
                newYear--;
            }
            const prevLastDay = getLastDayOfMonth(newYear, newMonth);
            navigateWithDay(newYear, newMonth, prevLastDay);
        } else if (day > lastDay) {
            let newMonth = currentMonth + 1;
            let newYear = currentYear;
            if (newMonth > 12) {
                newMonth = 1;
                newYear++;
            }
            navigateWithDay(newYear, newMonth, 1);
        } else {
            updateDayDisplay(day);
        }
    }

    function navigateWithDay(year, month, day) {
        window.location.href = `?year=${year}&month=${month}&day=${day}`;
    }

    if (dayArrowLeft) {
        dayArrowLeft.addEventListener('click', (e) => {
            moveDay(-1);
            e.target.blur();
        });
    }
    if (dayArrowRight) {
        dayArrowRight.addEventListener('click', (e) => {
            moveDay(1);
            e.target.blur();
        });
    }

    // URL에서 day 파라미터가 있으면 day-input에 반영
    const urlParams2 = new URLSearchParams(window.location.search);
    const urlDay = urlParams2.get('day');
    if (urlDay && dayInputHidden) {
        dayInputHidden.value = urlDay;
        const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(urlDay).padStart(2, '0')}`;
        populateDailyForm(dateStr);
        updateDayDisplay(urlDay);
    }
    setDayInputMinMax();

    // 네트워크/서버 에러 안내 메시지(기존 alert 외에 추가 안내)
    function showNetworkError(msg) {
        let errDiv = document.getElementById('network-error-msg');
        if (!errDiv) {
            errDiv = document.createElement('div');
            errDiv.id = 'network-error-msg';
            errDiv.style.position = 'fixed';
            errDiv.style.top = '10px';
            errDiv.style.left = '50%';
            errDiv.style.transform = 'translateX(-50%)';
            errDiv.style.background = '#ffcdd2';
            errDiv.style.color = '#b71c1c';
            errDiv.style.padding = '8px 24px';
            errDiv.style.border = '1px solid #e57373';
            errDiv.style.borderRadius = '6px';
            errDiv.style.zIndex = 9999;
            document.body.appendChild(errDiv);
        }
        errDiv.textContent = msg;
        errDiv.style.display = 'block';
        setTimeout(() => { errDiv.style.display = 'none'; }, 4000);
    }
    // 기존 fetchWithCsrf, populateDailyForm 등에서 catch(error)시 showNetworkError 호출하도록 필요시 추가

    $(document).on('click', '#copy-prev-month-btn', function() {
        if (!confirm('前月の情報を複写しますか？')) return;
        $.ajax({
            url: '/attendance/copy_prev_month/',
            type: 'POST',
            data: {
                year: currentYear,
                month: currentMonth,
                csrfmiddlewaretoken: csrfToken
            },
            success: function(data) {
                location.reload();
            },
            error: function(xhr) {
                alert('複写に失敗しました: ' + xhr.responseText);
            }
        });
    });

    function updateDayDisplay(day) {
        if (dayDisplay) dayDisplay.textContent = day;
        if (dayInputHidden) dayInputHidden.value = day;

        // 캘린더의 selected(파란색)도 같이 이동
        const allSelected = document.querySelectorAll('.calendar-table td.selected');
        allSelected.forEach(td => td.classList.remove('selected'));

        // 현재 연/월/일에 해당하는 셀에 selected 추가
        const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const td = document.querySelector(`.calendar-table td[data-date='${dateStr}']`);
        if (td) td.classList.add('selected');
    }

    // 승인/보내기 아이콘 클릭 이벤트
    document.querySelectorAll('.approval-icon').forEach(function(icon) {
        const required = parseInt(icon.dataset.required, 10);
        const confirmed = parseInt(icon.dataset.confirmed, 10);
        if (required === 0 && confirmed === 0) {
            icon.style.cursor = 'pointer';
            icon.addEventListener('click', function(e) {
                e.stopPropagation();
                // 날짜 정보 추출
                const td = icon.closest('td[data-date]');
                if (!td) return;
                const dateStr = td.getAttribute('data-date');
                // 서버에 is_required=1로 전송 (예시: fetch)
                fetch('/attendance/require_day/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ date: dateStr })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        // UI 갱신: 회색 보내기 아이콘으로 변경
                        icon.innerHTML = `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 9H14M14 9L10 5M14 9L10 13" stroke="#bdbdbd" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
                        icon.dataset.required = '1';
                        icon.style.cursor = 'default';
                    } else {
                        alert(data.message || '전송에 실패했습니다.');
                    }
                })
                .catch(() => alert('네트워크 오류로 전송에 실패했습니다.'));
            });
        }
    });

    // 日々承認 버튼 클릭 이벤트 (임시로 비활성화)
    /*
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.approval-btn.request-btn');
        if (btn) {
            e.preventDefault();
            const date = btn.dataset.date;
            if (!date) return;
            if (!confirm('この日の勤怠情報を承認申請しますか？')) return;
            try {
                const response = await fetchWithCsrf('/daily/approve/', {
                    method: 'POST',
                    body: JSON.stringify({ date })
                });
                const result = await response.json();
                if (result.status === 'success') {
                    alert('承認申請しました。');
                    window.location.reload();
                } else {
                    alert(result.message || '申請に失敗しました。');
                }
            } catch (err) {
                alert('通信エラーが発生しました。');
            }
        }
    });
    */

    // 근태등록 폼 비활성화/alert 처리
    function setDailyFormDisabled(disabled, message) {
        const form = document.getElementById('daily-entry-form');
        if (!form) return;
        [...form.elements].forEach(el => el.disabled = disabled);
        if (disabled && message) {
            alert(message);
        }
    }

    // 캘린더/리스트에서 날짜 클릭 시 상태에 따라 폼 제어
    function handleDailyFormLock(dayRecord) {
        if (!dayRecord) return setDailyFormDisabled(false);
        if (dayRecord.is_required == 1 && dayRecord.is_confirmed == 0) {
            setDailyFormDisabled(true, '承認申請中です。');
        } else if (dayRecord.is_required == 0 && dayRecord.is_confirmed == 1) {
            setDailyFormDisabled(true, 'すでに承認済みです。変更は管理者にご相談ください。');
        } else {
            setDailyFormDisabled(false);
        }
    }

    function showFormWarning(msg) {
        const warn = document.getElementById('form-warning');
        warn.style.display = 'flex';
        warn.querySelector('.warning-text').textContent = msg;
    }
    function hideFormWarning() {
        const warn = document.getElementById('form-warning');
        warn.style.display = 'none';
        warn.querySelector('.warning-text').textContent = '';
    }

    // 폼 원래 값 저장 및 복원 함수 (필요한 모든 필드 포함)
    let originalFormData = {};
    function saveOriginalFormData() {
        const form = document.getElementById('daily-entry-form');
        if (!form) return;
        originalFormData = {
            work_type: form.querySelector('[name="work_type"]').value,
            alternative_work_date: form.querySelector('[name="alternative_work_date"]').value,
            start_time: form.querySelector('[name="start_time"]').value,
            end_time: form.querySelector('[name="end_time"]').value,
            notes: form.querySelector('[name="notes"]').value
        };
    }
    function restoreOriginalFormData() {
        const form = document.getElementById('daily-entry-form');
        if (!form) return;
        form.querySelector('[name="work_type"]').value = originalFormData.work_type;
        form.querySelector('[name="alternative_work_date"]').value = originalFormData.alternative_work_date;
        form.querySelector('[name="start_time"]').value = originalFormData.start_time;
        form.querySelector('[name="end_time"]').value = originalFormData.end_time;
        form.querySelector('[name="notes"]').value = originalFormData.notes;
    }

    document.querySelectorAll('.attendance-list-row').forEach(row => {
        row.addEventListener('click', function() {
            const date = this.dataset.date;
            console.log('리스트 클릭 date:', date);
            hideFormWarning();
            populateDailyForm(date);

            // 연/월/일 표시 갱신
            if (date) {
                const [year, month, day] = date.split('-');
                // 연/월 부분 갱신
                const dateFullDiv = document.querySelector('.date-full');
                if (dateFullDiv) {
                    dateFullDiv.innerHTML = `${year}/${parseInt(month)}/<span id="day-display">${parseInt(day)}</span>`;
                }
                // dayInputHidden 값도 갱신
                const dayInputHidden = document.getElementById('day-input-hidden');
                if (dayInputHidden) {
                    dayInputHidden.value = parseInt(day);
                }
            }
        });
    });

    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10); // 'YYYY-MM-DD'

    // 오늘 날짜가 이번 달에 포함되어 있으면 자동 선택
    const thisYear = today.getFullYear();
    const thisMonth = today.getMonth() + 1;
    if (currentYear === thisYear && currentMonth === thisMonth) {
        populateDailyForm(todayStr);
        updateDayDisplay(today.getDate());
        // 캘린더 셀 하이라이트도 자동 적용됨
    }

    const monthlyInfoOpen = localStorage.getItem('monthlyInfoOpen');
    if (monthlyInfoOpen === '1') {
        monthlyInfoSection.style.display = '';
        showMonthlyInfoBtn.style.display = 'none';
        hideMonthlyInfoBtn.style.display = 'inline';
    } else {
        monthlyInfoSection.style.display = 'none';
        showMonthlyInfoBtn.style.display = 'inline';
        hideMonthlyInfoBtn.style.display = 'none';
    }

    // monthly_data가 있는지 체크 (템플릿에서 JS 변수로 넘겨주면 더 좋음)
    var hasMonthlyData = !!document.getElementById('list-tab'); // list-tab이 있으면 monthly_data 있음

    // 탭 상태 복원
    const selectedTab = localStorage.getItem('selectedTab');
    if (hasMonthlyData && selectedTab === 'list') {
        // 리스트 탭 활성화
        if (tabListBtn && tabCalendarBtn && listTab && calendarTab) {
            tabListBtn.classList.add('active');
            tabCalendarBtn.classList.remove('active');
            listTab.style.display = '';
            calendarTab.style.display = 'none';
        }
    } else {
        // 기본: 캘린더 탭 활성화
        if (tabCalendarBtn && tabListBtn && calendarTab && listTab) {
            tabCalendarBtn.classList.add('active');
            tabListBtn.classList.remove('active');
            calendarTab.style.display = '';
            listTab.style.display = 'none';
        }
    }


}); 