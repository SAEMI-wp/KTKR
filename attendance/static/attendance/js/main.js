// ===================== 전역 변수 및 상태 관리 =====================

// CSRF 토큰은 이미 window.csrfToken으로 설정됨

// 現在の状態を管理するグローバル変数
let currentState = {
    selectedDate: '',        // 選択された日付 (YYYY-MM-DD)
    calendarYear: 0,         // カレンダー表示年
    calendarMonth: 0,        // カレンダー表示月
    defaultDay: 0            // 今日の日 (固定値)
};

// バックアップ互換性をための変数
let currentYear, currentMonth;

// ===================== ユーティリティ関数 =====================

// CSRFを含むfetch関数 (セッション 有効期限切れ時 自動リダイレクト 含む)
function fetchWithCsrf(url, options = {}) {
    const defaultOptions = {
                headers: {
                    'X-CSRFToken': window.csrfToken,
            'Content-Type': 'application/json',
            ...options.headers
        },
        credentials: 'same-origin'
    };
    
    if (options.body instanceof FormData) {
        delete defaultOptions.headers['Content-Type'];
    }
    
    return fetch(url, { ...defaultOptions, ...options })
        .then(response => {
            // 세션 만료나 인증 실패 시 로그인 페이지로 리다이렉트
            if (response.status === 401 || response.status === 403) {
                console.log('[AUTH] セッションが失敗しました, ログイン ページに移動します.');
                window.location.href = '/login/';
                return Promise.reject(new Error('Session expired'));
            }
            return response;
        });
}

// 日付関連 ユーティリティ
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function parseDate(dateStr) {
    console.log(`[PARSE] 날짜 파싱 시작: ${dateStr}`);
    
    // YYYY-MM-DD形式 処理
    if (dateStr.includes('-')) {
        const [year, month, day] = dateStr.split('-').map(Number);
        const result = new Date(year, month - 1, day);
        console.log(`[PARSE] YYYY-MM-DD 형식 파싱 결과: ${result}`);
        return result;
    }
    
    // YYYY/MM/DD形式 処理
    if (dateStr.includes('/')) {
        const [year, month, day] = dateStr.split('/').map(Number);
        const result = new Date(year, month - 1, day);
        console.log(`[PARSE] YYYY/MM/DD 형식 파싱 결과: ${result}`);
        return result;
    }
    
    // 日本語形式 (YYYY年M月D日) 処理
    const japaneseMatch = dateStr.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (japaneseMatch) {
        const year = parseInt(japaneseMatch[1]);
        const month = parseInt(japaneseMatch[2]);
        const day = parseInt(japaneseMatch[3]);
        const result = new Date(year, month - 1, day);
        console.log(`[PARSE] YYYY年M月D日 형식 파싱 결과: ${result}`);
        return result;
    }
    
    console.error(`[PARSE] 지원하지 않는 날짜 형식: ${dateStr}`);
    return new Date(); // 기본값 반환
}

function getTodayDate() {
    return formatDate(new Date());
}

// ===================== ナビゲーション関数 =====================

// カレンダーまたはリストを特定の年月に更新 (ページリロード)
function navigate(year, month, day) {
    let url = `?year=${year}&month=${month}`;
    if (day) url += `&day=${day}`;
    window.location.href = url;
}

// ホームに戻る (今日の日付)
function goToToday() {
    const today = new Date();
    console.log(`[HOME] 今日に移動: ${getTodayDate()}`);
    navigate(today.getFullYear(), today.getMonth() + 1, today.getDate());
}

// ===================== 月月情報 トグル 管理 関数 =====================

// サーバーでトグル状態を処理

/**
 * 月情報 セクションをAJAXで読み込む関数
 * @param {number} year - 年
 * @param {number} month - 月
 * @returns {Promise<boolean>} - 月情報 存在 有無
 */
async function loadMonthlyInfoSection(year, month) {
    try {
        console.log(`[MONTHLY_INFO] 月情報 読み込み開始: ${year}-${month}`);
        
        const url = `/attendance/monthly-info/section/?year=${year}&month=${month}`;
        const response = await fetchWithCsrf(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP エラー! status: ${response.status}`);
        }
        
        const html = await response.text();
        const container = document.getElementById('monthly-info-container');
        
        if (container) {
            container.innerHTML = html;
            container.style.display = 'block';
            console.log(`[MONTHLY_INFO] 月情報 読み込み完了: ${year}-${month}`);
            
            // 月情報 修正 ボタン イベント ハンドラ 登録
            const editMonthlyBtn = container.querySelector('#edit-monthly-btn');
            if (editMonthlyBtn) {
                editMonthlyBtn.addEventListener('click', MonthlyUpdateModalModule.open);
                console.log('[MONTHLY_INFO] 월정보 수정 버튼 이벤트 등록 완료');
            }
            
            // 月情報修正モーダルの閉じるボタンとフォームイベントも登録
            const closeUpdateModalBtn = document.getElementById('close-update-modal-btn');
            const monthlyUpdateForm = document.getElementById('monthly-update-form');
            
            if (closeUpdateModalBtn) {
                closeUpdateModalBtn.addEventListener('click', MonthlyUpdateModalModule.close);
            }
            
            if (monthlyUpdateForm) {
                monthlyUpdateForm.addEventListener('submit', MonthlyUpdateModalModule.submit);
            }
            
            // 月情報 存在 確認
            const monthlySection = container.querySelector('#monthly-info-section');
            const hasMonthlyData = monthlySection !== null;
            
            // 月情報 警告 状態 更新 (新規追加)
            if (currentState.selectedDate) {
                updateMonthlyDataWarning(currentState.selectedDate);
            }
            
            // 月情報 登録 ボタン イベント 登録
            const createMonthlyBtn = container.querySelector('#create-monthly-btn');
            if (createMonthlyBtn) {
                createMonthlyBtn.addEventListener('click', MonthlyModalModule.open);
                console.log('[MONTHLY_INFO] 月情報 登録 ボタン イベント 登録 完了');
            }
            
            // 月情報 登録 モーダルの閉じるボタンとフォームイベントも登録
            const closeModalBtn = document.getElementById('close-modal-btn');
            const monthlyForm = document.getElementById('monthly-form');
            
            if (closeModalBtn) {
                closeModalBtn.addEventListener('click', MonthlyModalModule.close);
            }
            
            if (monthlyForm) {
                monthlyForm.addEventListener('submit', MonthlyModalModule.submit);
            }
 
            return hasMonthlyData;
        }
        
        return false;
        
    } catch (error) {
        console.error(`[MONTHLY_INFO] 月情報 読み込み失敗: ${error}`);
        
        // エラー時 月情報 コンテナとタブスイッチ 隠し
        const container = document.getElementById('monthly-info-container');
        const tabSwitcher = document.getElementById('tab-switcher');
        if (container) container.style.display = 'none';
        if (tabSwitcher) tabSwitcher.style.display = 'none';
        
        return false;
    }
}

/**
 * トグル ボタン クリック イベント ハンドラ
 * @returns {Promise<void>}
 */
async function handleMonthlyInfoToggle() {
    const toggleBtn = document.getElementById('monthly-info-toggle-btn');
    if (!toggleBtn) return;
    
    // 現在ボタン状態確認
    const isGreen = toggleBtn.classList.contains('green');
    
    // トグル状態更新
    const newToggleState = isGreen ? '1' : '0';
    localStorage.setItem('monthlyInfoOpen', newToggleState);
    
    // 現在の年月 取得
    const currentMonthDisplay = document.getElementById('current-month-display');
    if (!currentMonthDisplay) {
        console.error('[TOGGLE] 現在の年月の情報を見つけることができません');
        return;
    }
    
    const year = parseInt(currentMonthDisplay.dataset.year);
    const month = parseInt(currentMonthDisplay.dataset.month);
    
    if (!year || !month) {
        console.error('[TOGGLE] 年月情報が無効です');
        return;
    }
    
    // AJAXで全カレンダーセクション再読み込み (사용자 의도를 서버에 전달)
    console.log(`[TOGGLE] トグル状態変更: ${isGreen ? 'green' : 'red'} → ${isGreen ? 'red' : 'green'}`);
    await updateCalendarSection(year, month, null, newToggleState);
}

// ===================== 状態 初期化 =====================
// 初期状態をDOMから読み取り
function initializeState() {
    // window.initialDataからパースされた初期値を取得
    if (window.initialData) {
        currentState.selectedDate = window.initialData.selectedDate;
        currentState.calendarYear = window.initialData.currentYear;
        currentState.calendarMonth = window.initialData.currentMonth;
        currentState.defaultDay = window.initialData.defaultDay;
        
        // バックアップ互換性
        currentYear = currentState.calendarYear;
        currentMonth = currentState.calendarMonth;
        } else {
        // fallback: DOMから読み取り
        const dayDisplayEl = document.getElementById('day-display');
        const currentMonthDisplayEl = document.getElementById('current-month-display');
        
        if (dayDisplayEl) {
            const displayText = dayDisplayEl.textContent.trim();
            // YYYY/MM/DD形式の処理
            if (displayText.match(/^\d{4}\/\d{1,2}\/\d{1,2}$/)) {
                const [year, month, day] = displayText.split('/').map(Number);
                currentState.selectedDate = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            }
        }
        
        if (currentMonthDisplayEl) {
            currentState.calendarYear = parseInt(currentMonthDisplayEl.dataset.year);
            currentState.calendarMonth = parseInt(currentMonthDisplayEl.dataset.month);
            currentYear = currentState.calendarYear;
            currentMonth = currentState.calendarMonth;
        }
        
        const today = new Date();
        currentState.defaultDay = today.getDate();
    }
    
    // DOMが読み込まれた後にフォームの初期化を確認
    const dayDisplayEl = document.getElementById('day-display');
    if (dayDisplayEl && (!dayDisplayEl.textContent || dayDisplayEl.textContent.trim() === '')) {
        console.log('[STATE] day-displayが空です, 強制的に更新');
        if (currentState.selectedDate) {
            const parsedDate = parseDate(currentState.selectedDate);
            const year = parsedDate.getFullYear();
            const month = parsedDate.getMonth() + 1;
            const day = parsedDate.getDate();
            
            dayDisplayEl.textContent = `${year}/${month}/${day}`;
            
            const dayInputHiddenEl = document.getElementById('day-input-hidden');
            if (dayInputHiddenEl) {
                dayInputHiddenEl.value = day;
            }
        }
    }
    
    console.log('[STATE] 初期化完了:', currentState);
}

// ===================== データ 処理 関数 =====================

// 셀이나 행에서 일일 데이터 추출
function getDailyDataFromCell(element) {
    if (!element) return null;
    
    // 리스트 행인 경우 data attributes에서 추출
    if (element.classList.contains('attendance-list-row')) {
        const hasRecord = element.dataset.hasRecord === '1';
        if (!hasRecord) return null;
        
        // 각 td에서 데이터 추출
        const cells = element.querySelectorAll('td');
        if (cells.length < 7) return null;
        
        // 비고란에서 삭제 버튼 제외하고 텍스트만 추출
        const notesCell = cells[6];
        let notesText = '';
        if (notesCell) {
            const notesContent = notesCell.querySelector('.notes-content');
            if (notesContent) {
                // 삭제 버튼을 제외한 텍스트만 가져오기
                const notesTextNode = notesContent.childNodes[0]; // 첫 번째 텍스트 노드
                notesText = notesTextNode ? notesTextNode.textContent.trim() : '';
            } else {
                notesText = notesCell.textContent.trim() || '';
            }
        }
        
        // 勤務区分 처리: 비어있으면 '出勤'으로 처리
        let workType = cells[2].textContent.trim();
        if (!workType) {
            workType = '出勤';  // 리스트에서 비어있으면 출근으로 처리
        }
        
        const result = {
            work_type: workType,
            start_time: cells[3].textContent.trim() || '',
            end_time: cells[4].textContent.trim() || '',
            alternative_work_date1: cells[5].textContent.trim().split('\n')[0] || '',
            alternative_work_date2: cells[5].textContent.trim().split('\n')[1] || '',
            alternative_work_date3: cells[5].textContent.trim().split('\n')[2] || '',
            notes: notesText
        };
        
        console.log('[GET DATA] 리스트에서 가져온 데이터:', result);
        return result;
    }
    
    // 캘린더 셀인 경우 data attributes에서 추출
    return {
        work_type: element.dataset.workType || '',
        start_time: element.dataset.startTime || '',
        end_time: element.dataset.endTime || '',
        alternative_work_date1: element.dataset.alternativeWorkDate1 || '',
        alternative_work_date2: element.dataset.alternativeWorkDate2 || '',
        alternative_work_date3: element.dataset.alternativeWorkDate3 || '',
        notes: element.dataset.notes || ''
    };
}

// 기본 근무구분 결정
/**
 * 日付に基づいてデフォルト勤務区分を取得
 * 祝日、土日、平日の順で判定
 */
function getDefaultWorkType(dateString) {
    console.log(`[DEFAULT WORK TYPE] 日付: ${dateString}`);
    
    // 祝日判定を最優先
    const holidayType = getHolidayTypeByDate(dateString);
    console.log(`[DEFAULT WORK TYPE] 祝日判定結果: ${holidayType}`);
    
    if (holidayType) {
        console.log(`[DEFAULT WORK TYPE] 祝日として判定: ${holidayType}`);
        return holidayType;
    }
    
    // 土日判定
    const date = parseDate(dateString);
    const dayOfWeek = date.getDay(); // 0=일요일, 6=토요일
    
    if (dayOfWeek === 0) {
        console.log(`[DEFAULT WORK TYPE] 日曜日として判定: 休日(法)`);
        return '休日(法)'; // 일요일
    }
    if (dayOfWeek === 6) {
        console.log(`[DEFAULT WORK TYPE] 土曜日として判定: 休日`);
        return '休日'; // 토요일
    }
    
    console.log(`[DEFAULT WORK TYPE] 平日として判定: 出勤`);
    return '出勤'; // 평일
}

/**
 * フォームにデータを入力し、祝日の場合勤務区分オプションを制限
 */
function populateFormWithData(dailyData, defaultWorkType) {
    console.log('[FORM] フォームデータ入力:', dailyData, defaultWorkType);
            
    const form = document.getElementById('daily-entry-form');
    if (!form) {
        console.warn('[FORM] フォームを見つけられません');
        return;
    }
    
    // 現在選択された日付を取得
    const currentDate = currentState.selectedDate;
    
    // 既存のデータがある場合はそのデータで入力
    if (dailyData) {
        const workTypeSelect = form.querySelector('[name="work_type"]');
        const startTimeInput = form.querySelector('[name="start_time"]');
        const endTimeInput = form.querySelector('[name="end_time"]');
        const altDateInput1 = form.querySelector('[name="alternative_work_date1"]');
        const altDateInput2 = form.querySelector('[name="alternative_work_date2"]');
        const altDateInput3 = form.querySelector('[name="alternative_work_date3"]');
        const notesInput = form.querySelector('[name="notes"]');
        
        if (workTypeSelect) workTypeSelect.value = dailyData.work_type || '';
        if (startTimeInput) startTimeInput.value = dailyData.start_time || '00:00:00';
        if (endTimeInput) endTimeInput.value = dailyData.end_time || '00:00:00';
        if (altDateInput1) altDateInput1.value = dailyData.alternative_work_date1 || '';
        if (altDateInput2) altDateInput2.value = dailyData.alternative_work_date2 || '';
        if (altDateInput3) altDateInput3.value = dailyData.alternative_work_date3 || '';
        if (notesInput) notesInput.value = dailyData.notes || '';
        
        console.log('[FORM] 既存データでフォーム入力');
    } else {
        // 新規データの場合は基本値を設定
        const workTypeSelect = form.querySelector('[name="work_type"]');
        if (workTypeSelect && defaultWorkType) {
            workTypeSelect.value = defaultWorkType;
            console.log(`[FORM] 基本勤務区分設定: ${defaultWorkType}`);
        }
        
        // 他のフィールドは初期化
        const startTimeInput = form.querySelector('[name="start_time"]');
        const endTimeInput = form.querySelector('[name="end_time"]');
        const altDateInput1 = form.querySelector('[name="alternative_work_date1"]');
        const altDateInput2 = form.querySelector('[name="alternative_work_date2"]');
        const altDateInput3 = form.querySelector('[name="alternative_work_date3"]');
        const notesInput = form.querySelector('[name="notes"]');
        
        if (startTimeInput) startTimeInput.value = '00:00:00';
        if (endTimeInput) endTimeInput.value = '00:00:00';
        if (altDateInput1) altDateInput1.value = '';
        if (altDateInput2) altDateInput2.value = '';
        if (altDateInput3) altDateInput3.value = '';
        if (notesInput) notesInput.value = '';
        
        console.log('[FORM] 新規データでフォーム初期化');
    }
    
    // 休日、休日(法)、祝日の場合、勤務区分オプションを制限
    if (currentDate) {
        filterWorkTypeOptionsByDate(currentDate);
        console.log(`[FORM] ${currentDate}の勤務区分オプション制限適用`);
    }
    
    // 勤務区分に応じてフォーム状態を同時化 (保存されたデータでも新規データでも常に適用)
    const workTypeSelect = form.querySelector('[name="work_type"]');
    if (workTypeSelect) {        
        toggleAltWorkDateField(workTypeSelect.value);
        
        // 勤務区分に応じてフォーム状態を同時化 (時間入力フィールド, 通常ボタンなど)
        const startTimeInput = form.querySelector('[name="start_time"]');
        const endTimeInput = form.querySelector('[name="end_time"]');
        const normalHoursBtn = document.getElementById('normal-hours-btn');
        
        console.log('[FORM] 폼 요소들:', {
            startTimeInput: startTimeInput,
            endTimeInput: endTimeInput,
            normalHoursBtn: normalHoursBtn
        });
        
        // ★ 핵심: 저장된 데이터든 새 데이터든 항상 버튼 상태 동기화
        if (startTimeInput && endTimeInput && normalHoursBtn) {
            syncFormStateByWorkType(workTypeSelect.value, startTimeInput, endTimeInput, normalHoursBtn);
            console.log(`[FORM] 근무구분에 따른 폼 상태 동기화 완료: ${workTypeSelect.value}`);
        }
    } else {
        console.warn('[FORM] 근무구분 필드를 찾을 수 없습니다');
    }
}

// 월별 데이터 경고 숨기기
function hideMonthlyDataWarning() {
    hideFormWarning();
    console.log('[FORM] 월별 데이터 경고 숨김');
}

// 월별 데이터 경고 표시
function showMonthlyDataWarning() {
    showFormWarning('月情報を先に登録してください。');
    console.log('[FORM] 월별 데이터 경고 표시');
}

// 月情報がある場合は警告を非表示にし、月情報がない場合は警告を表示する
async function updateMonthlyDataWarning(selectedDate) {
    if (!selectedDate) {
        console.warn('[FORM] 選択された日付がないため、警告状態の更新をスキップします');
        return;
    }
    
    try {
        const hasMonthlyData = await checkMonthlyDataForSelectedDate(selectedDate);
        console.log(`[FORM] 警告状態の更新: ${selectedDate} -> 月情報 ${hasMonthlyData ? 'あり' : 'なし'}`);
        
        if (hasMonthlyData) {
            hideMonthlyDataWarning();
        } else {
            showMonthlyDataWarning();
        }
    } catch (error) {
        console.error('[FORM] 警告状態の更新に失敗しました:', error);
        // エラーが発生した場合は警告を表示
        showMonthlyDataWarning();
    }
}

// ===================== DOM 업데이트 함수 =====================


// 캘린더 파란 셀 표시 업데이트
function updateCalendarHighlight() {
    // 기존 선택 모두 제거
    const previousSelected = document.querySelectorAll('.calendar-table td.selected');
    previousSelected.forEach(cell => {
        cell.classList.remove('selected');
    });
    
    // 선택된 날짜가 현재 캘린더 년월과 일치하는지 확인
    const selectedDate = parseDate(currentState.selectedDate);
    const selectedYear = selectedDate.getFullYear();
    const selectedMonth = selectedDate.getMonth() + 1;
    const selectedDay = selectedDate.getDate();
    
    if (selectedYear === currentState.calendarYear && selectedMonth === currentState.calendarMonth) {
        // 해당 일자의 셀 찾기
        const calendarCells = document.querySelectorAll('.calendar-table td');
        for (const cell of calendarCells) {
            const dateNumber = cell.querySelector('.date-number');
            if (dateNumber && parseInt(dateNumber.textContent) === selectedDay) {
                if (!cell.classList.contains('other-month')) {
                    cell.classList.add('selected');
                    console.log(`[HIGHLIGHT] 青いセル設定: ${selectedDay}日`);
                    break;
                }
            }
        }
    } else {
        console.log(`[HIGHLIGHT] 선택일(${selectedYear}-${selectedMonth})과 캘린더(${currentState.calendarYear}-${currentState.calendarMonth})가 다름`);
    }
}



// ===================== AJAX 섹션 업데이트 함수 =====================

// 날짜 표시 업데이트
function updateDateDisplay(dateString) {
    console.log(`[FORM] 날짜 표시 업데이트: ${dateString}`);
    
    const dayDisplayEl = document.getElementById('day-display');
    const dayInputHiddenEl = document.getElementById('day-input-hidden');
    
    if (!dayDisplayEl || !dayInputHiddenEl) {
        console.warn('[FORM] 날짜 표시 요소를 찾을 수 없습니다');
        return;
    }
    
    try {
        const parsedDate = parseDate(dateString);
        const year = parsedDate.getFullYear();
        const month = parsedDate.getMonth() + 1;
        const day = parsedDate.getDate();
        
        dayDisplayEl.textContent = `${year}/${month}/${day}`;
        dayInputHiddenEl.value = day;
        
        // 상태 업데이트 (YYYY-MM-DD 형식으로 통일)
        currentState.selectedDate = dateString;
        
        console.log(`[FORM] 날짜 표시 업데이트 완료: ${dayDisplayEl.textContent}`);
    } catch (error) {
        console.error('[FORM] 날짜 표시 업데이트 오류:', error);
    }
}

// フォームセクション更新
async function updateFormSection(selectedDate) {
    console.log(`[FORM] フォーム更新 for: ${selectedDate}`);
    
    try {
        const response = await fetchWithCsrf(`/attendance/form_partial/?date=${selectedDate}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const html = await response.text();
        
        // 一時的なdivを作成してHTMLを解析
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // 全体form sectionを置き換えてサーバーの非活性化状態を反映
        const formSection = document.getElementById('form-section');
        if (formSection) {
            // 全体HTMLを置き換え
            formSection.innerHTML = html;
            
            // すべてのフォームイベントを再バインド
            rebindFormEvents();
            
            // フォームの状態同期化
            const form = document.getElementById('daily-entry-form');
            if (form) {
                const workTypeSelect = form.querySelector('[name="work_type"]');
                if (workTypeSelect) {
                    console.log(`[FORM] フォームロード後の勤務区分状態の同期化: ${workTypeSelect.value}`);
                    toggleAltWorkDateField(workTypeSelect.value);
                }
            }
        }
        
    } catch (error) {
        console.error('[FORM] 更新エラー:', error);
    }
}

// カレンダーセクション更新  (show_list パラメーターは常に渡す)
async function updateCalendarSection(year, month, showListParam = null, toggleState = null) {
    console.log(`[CALENDAR] カレンダー更新: ${year}-${month}`);
    
    try {
        // パラメーターがない場合はlocalStorageから取得
        if (showListParam === null) {
            const isListTabActive = localStorage.getItem('selectedTab') === 'list';
            showListParam = isListTabActive ? '1' : '0';
        }
        if (toggleState === null) {
            // toggleState가 null이면 서버가 월정보 유무에 따라 결정하도록 함
            toggleState = null;
        }
        
        // URL 구성 - toggleState가 null이면 파라미터에서 제외
        let url = `/attendance/calendar_partial/?year=${year}&month=${month}&show_list=${showListParam}`;
        if (toggleState !== null) {
            url += `&toggle_state=${toggleState}`;
        }
        
        const response = await fetchWithCsrf(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const html = await response.text();
        
        // 캘린더 섹션 업데이트 로직
        const calendarSection = document.getElementById('calendar-section');
        if (calendarSection) {
            calendarSection.innerHTML = html;
            console.log('[CALENDAR] 캘린더 섹션 업데이트 완료');
        }
        
    } catch (error) {
        console.error('[CALENDAR] 更新エラー:', error);
    }
}

// カレンダーセクション更新  (show_list パラメーターは常に渡す)
async function updateCalendarSection(year, month, showListParam = null, toggleState = null) {
    console.log(`[CALENDAR] カレンダー更新: ${year}-${month}`);
    
    try {
        // パラメーターがない場合はlocalStorageから取得
        if (showListParam === null) {
            const isListTabActive = localStorage.getItem('selectedTab') === 'list';
            showListParam = isListTabActive ? '1' : '0';
        }
        if (toggleState === null) {
            // 서버가 월정보 유무에 따라 결정하도록 함 (localStorage 체크 안함)
            toggleState = null;
        }
        
        // URL 구성 - toggleState가 null이면 파라미터에서 제외
        let url = `/attendance/calendar_partial/?year=${year}&month=${month}&show_list=${showListParam}`;
        if (toggleState !== null) {
            url += `&toggle_state=${toggleState}`;
        }
        
        // AJAXリクエスト
        const response = await fetchWithCsrf(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const html = await response.text();
        
        // 一時的なdivを作成してHTMLを解析
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        const calendarSection = document.getElementById('calendar-section');
        if (calendarSection) {
            const dateSelector = tempDiv.querySelector('.date-selector');
            const monthlyInfoContainer = tempDiv.querySelector('#monthly-info-container');
            const toggleButtons = tempDiv.querySelectorAll('.toggle-btn, .copy-prev-month-btn');
            const tabSwitcher = tempDiv.querySelector('.tab-switcher');
            
            // 基本構造の更新
            calendarSection.innerHTML = '';
            
            // 日付選択コンテナの追加
            if (dateSelector) {
                calendarSection.appendChild(dateSelector.cloneNode(true));
            }
            
            // トグルボタンの追加
            toggleButtons.forEach(btn => {
                const clonedBtn = btn.cloneNode(true);
                calendarSection.appendChild(clonedBtn);
            });
            
            // 月情報コンテナの追加 (空の状態で)
            if (monthlyInfoContainer) {
                calendarSection.appendChild(monthlyInfoContainer.cloneNode(true));
            }
            
            // タブスイッチの追加 (常に表示)
            if (tabSwitcher) {
                const clonedTabSwitcher = tabSwitcher.cloneNode(true);
                calendarSection.appendChild(clonedTabSwitcher);
            }
            
            console.log('[CALENDAR] 기본 구조 렌더링 완료');
            
            // 2단계: 서버에서 렌더링된 토글 버튼 상태 확인하여 월정보 로딩
            const toggleBtn = document.getElementById('monthly-info-toggle-btn');
            if (toggleBtn && toggleBtn.classList.contains('red')) {
                // 서버에서 red 버튼으로 렌더링됨 = 월정보가 없거나 사용자가 열어둔 상태
                console.log('[CALENDAR] 서버에서 red 버튼으로 렌더링됨 - 월정보 로딩 시작');
                loadMonthlyInfoSection(year, month).then(hasMonthlyData => {
                    if (hasMonthlyData) {
                        console.log('[CALENDAR] 월정보 로딩 완료 (데이터 있음) - localStorage에 상태 저장');
                        // 월정보가 있으면 사용자 상태를 localStorage에 저장
                        localStorage.setItem('monthlyInfoOpen', '1');
                    } else {
                        console.log('[CALENDAR] 월정보 로딩 완료 (데이터 없음) - 사용자가 닫을 수 있도록 상태 저장');
                        // 월정보가 없어도 사용자가 닫을 수 있도록 상태 저장
                        localStorage.setItem('monthlyInfoOpen', '1');
                    }
                });
            } else {
                console.log('[CALENDAR] 서버에서 green 버튼으로 렌더링됨 - 월정보 로딩 안함');
                // 월정보가 있고 사용자가 닫아둔 상태
                localStorage.setItem('monthlyInfoOpen', '0');
            }
            
            const calendarTab = tempDiv.querySelector('#calendar-tab');
            const listTab = tempDiv.querySelector('#list-tab');
            
            // 캘린더 탭 추가
            if (calendarTab) {
                calendarSection.appendChild(calendarTab.cloneNode(true));
            }
            
            // 리스트 탭 추가
            if (listTab) {
                calendarSection.appendChild(listTab.cloneNode(true));
            }
            
            // PDFプレビューボタンの이벤트を再バインド
            setupPrintPreviewLogic();
            
            // 상태 업데이트
            currentState.calendarYear = year;
            currentState.calendarMonth = month;
            currentYear = year;
            currentMonth = month;
            
            // 3단계: 이벤트 재등록 및 하이라이트 업데이트
            initializeCalendarEvents();
            initializeListEvents(); // 리스트 이벤트 재등록
            initializeTabSwitching(false); // 탭 이벤트 재등록
            
            applyAllHolidaysToCalendar();
            updateCalendarHighlight();
            
            // AJAX로 로드된 콘텐츠에 이벤트 리스너 바인딩
            bindSurveyButtonEvents();
            
            // 월정보 경고 상태 업데이트 (새로 추가)
            if (currentState.selectedDate) {
                updateMonthlyDataWarning(currentState.selectedDate);
            }
            
            console.log('[CALENDAR] 캘린더/리스트 렌더링 완료');
        }
        
    } catch (error) {
        console.error('[CALENDAR] 更新エラー:', error);
    }
}

// ===================== 이벤트 핸들러 =====================

// 리스트 행 클릭 핸들러
function handleListRowClick(event) {
    console.log('[LIST] 리스트 행 클릭');
    const row = event.currentTarget;
    const date = row.dataset.date;
    const defaultWorkType = row.dataset.defaultWorkType;
    const hasRecord = row.dataset.hasRecord;
    
    console.log('[LIST] 행 정보:', {
        date: date,
        defaultWorkType: defaultWorkType,
        hasRecord: hasRecord,
        element: row
    });
    
    if (!date) {
        console.warn('[LIST] 행에 date 속성이 없습니다');
                return;
            }
            
    console.log(`[LIST] 날짜 선택: ${date}, 기본 근무구분: ${defaultWorkType}`);
    
    // 경고 메시지 숨기기
    hideMonthlyDataWarning();
    
    // 선택된 날짜 업데이트
    currentState.selectedDate = date;
    
    // 날짜 표시 업데이트
    updateDateDisplay(date);
    
    // 해당 날짜의 데이터로 폼 채우기
    const dailyData = getDailyDataFromCell(row);
    
    // 기존 데이터가 있으면 그대로 사용, 없을 때만 기본값 적용
    let finalWorkType = '';
    if (dailyData && dailyData.work_type) {
        // 기존 데이터가 있으면 그대로 사용
        finalWorkType = dailyData.work_type;
        console.log('[LIST] 기존 데이터의 근무구분 사용:', finalWorkType);
    } else {
        // 기존 데이터가 없을 때만 기본값 적용
        finalWorkType = defaultWorkType || getDefaultWorkType(date);
        console.log('[LIST] 기본 근무구분 적용:', finalWorkType);
    }
    
    console.log('[LIST] 폼 채우기 데이터:', {
        dailyData: dailyData,
        defaultWorkType: defaultWorkType,
        finalWorkType: finalWorkType
    });
    
    populateFormWithData(dailyData, finalWorkType);
    
    // カレンダーハイライト更新 (同じ月の場合)
    const selectedDate = parseDate(date);
    if (selectedDate.getFullYear() === currentState.calendarYear && 
        (selectedDate.getMonth() + 1) === currentState.calendarMonth) {
        updateCalendarHighlight();
    }
    
    // 月情報警告状態の更新 (新規追加)
    updateMonthlyDataWarning(date);
}

// カレンダーセルクリック処理
function handleCalendarCellClick(event) {
    const cell = event.currentTarget;
    let date = cell.dataset.date;
    
    // data-dateがない場合は計算
    if (!date) {
        const dateNumber = cell.querySelector('.date-number');
        if (dateNumber && !cell.classList.contains('other-month')) {
            const day = parseInt(dateNumber.textContent);
            date = `${currentState.calendarYear}-${String(currentState.calendarMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                } else {
            return; //クリック不可能なセル
        }
    }
    
    console.log(`[CELL] カレンダーセルクリック: ${date}`);
    
    // 選択された日付の状態を即時更新
    currentState.selectedDate = date;
    
    // 即時にハイライトを更新 (フォーム更新前に)
    updateCalendarHighlight();
    
    // フォーム更新 (選択された日付の変更)
    updateFormSection(date);
    
    // 月情報警告状態の更新 (新規追加)
    updateMonthlyDataWarning(date);
}



// Day Arrowボタンの処理
function handleDayArrowClick(direction) {
    console.log(`[DAY_ARROW] 開始: ${direction}, 現在の選択日: ${currentState.selectedDate}`);
    
    if (!currentState.selectedDate) {
        console.warn('[DAY_ARROW] 選択された日付がありません。');
        return;
    }
    
    const selectedDate = parseDate(currentState.selectedDate);
    if (isNaN(selectedDate.getTime())) {
        console.error('[DAY_ARROW] 日付解析失敗:', currentState.selectedDate);
        return;
    }
    
    let newDate = new Date(selectedDate);
    
    if (direction === 'prev') {
        newDate.setDate(newDate.getDate() - 1);
    } else {
        newDate.setDate(newDate.getDate() + 1);
    }
    
    const newDateStr = formatDate(newDate);
    const newYear = newDate.getFullYear();
    const newMonth = newDate.getMonth() + 1;
    
    console.log(`[DAY_ARROW] 日付移動: ${currentState.selectedDate} → ${newDateStr}`);
    
    // 月が変わり、現在のカレンダーと選択日の年月が同じ場合にのみカレンダーも移動
    const currentSelectedDate = parseDate(currentState.selectedDate);
    const currentSelectedYear = currentSelectedDate.getFullYear();
    const currentSelectedMonth = currentSelectedDate.getMonth() + 1;
    
    if (newYear !== currentSelectedYear || newMonth !== currentSelectedMonth) {
        // 月境界を越えた
        if (currentSelectedYear === currentState.calendarYear && currentSelectedMonth === currentState.calendarMonth) {
            // 現在のカレンダーと選択日が同じ年月であればカレンダーも同時に移動
            console.log(`[DAY_ARROW] 月境界越え - カレンダーも移動: ${newYear}-${newMonth}`);
            updateCalendarSection(newYear, newMonth);
        }
    }
    
    // 状態を先に更新
    currentState.selectedDate = newDateStr;
    
    // フォーム更新
    updateFormSection(newDateStr);
    
    // 月情報警告状態の更新 (新規追加)
    updateMonthlyDataWarning(newDateStr);
    
    // カレンダーが同じ年月であればハイライトを更新
    if (newYear === currentState.calendarYear && newMonth === currentState.calendarMonth) {
        setTimeout(() => {
            updateCalendarHighlight();
        }, 100);
    }
}

// 월 네비게이션 처리 (AJAX로 캘린더만 이동, 선택일은 변경하지 않음)
function handleMonthNavigation(direction) {
    let newYear = currentState.calendarYear;
    let newMonth = currentState.calendarMonth;
    
    console.log(`[MONTH_NAV] 시작: ${direction}, 현재: ${newYear}-${newMonth}`);
    
    if (direction === 'prev') {
        newMonth -= 1;
        if (newMonth < 1) {
            newMonth = 12;
            newYear -= 1;
        }
    } else {
        newMonth += 1;
        if (newMonth > 12) {
            newMonth = 1;
            newYear += 1;
        }
    }
    
    console.log(`[MONTH_NAV] 계산 결과: ${newYear}-${newMonth}`);
    
    // 현재 상태 업데이트
    currentState.calendarYear = newYear;
    currentState.calendarMonth = newMonth;
    
    // 현재 탭 상태 확인하여 show_list 파라미터 유지
    const isListTabActive = localStorage.getItem('selectedTab') === 'list';
    const showListParam = isListTabActive ? '1' : '0';
    // toggleState는 null로 전달하여 서버가 월정보 유무에 따라 결정하도록 함
    const toggleState = null;
    
    // AJAX로 partial 갱신
    updateCalendarSection(newYear, newMonth, showListParam, toggleState);
}

// フォーム提出処理
async function handleFormSubmit(event) {
    event.preventDefault();
    console.log('[FORM] フォーム提出');
    
    const form = event.target;
    const formData = new FormData(form);
    
    // 1. 選択された日付の月情報を確認
    console.log('[FORM] 선택된 날짜:', currentState.selectedDate);
    
    const hasMonthlyData = await checkMonthlyDataForSelectedDate(currentState.selectedDate);
    
    console.log('[FORM] 월정보 체크 결과:', hasMonthlyData);
    
    if (!hasMonthlyData) {
        showMonthlyDataWarning();
        console.log('[FORM] 선택된 날짜의 월정보 없음, 등록 차단');
        return;
    }
    
    // 2. 代休/振替の勤務日バリデーション
    const workType = formData.get('work_type');
    const alternativeWorkDate1 = formData.get('alternative_work_date1');
    const alternativeWorkDate2 = formData.get('alternative_work_date2');
    const alternativeWorkDate3 = formData.get('alternative_work_date3');
    const requiredAltWorkTypes = ['代休', '振替(勤)', '振替(休)']; // 필수 입력이 필요한 근무구분들
    
    if (requiredAltWorkTypes.includes(workType) && !alternativeWorkDate1) {
        showFormWarning('代休/振替の勤務日を入力してください。');
        const altInput = document.getElementById('alt-work-date-group')?.querySelector('input[type="date"]');
        if (altInput) {
            altInput.focus();
        }
        return;
    }
    
    // 3. 勤務時間のチェック (出勤, 退勤, 代休, 代休退勤の場合)
    const startTime = formData.get('start_time');
    const endTime = formData.get('end_time');
    const workTypesRequiringTime = ['出勤', '代休', '振替(勤)'];
    
    if (workTypesRequiringTime.includes(workType)) {
        if (!startTime || !endTime) {
            showFormWarning('始時刻と了時刻を入力してください。');
            console.log('[FORM] 시간 입력 없음, 등록 차단');
            return;
        }
        
        if (startTime === endTime) {
            showFormWarning('始時刻と了時刻は異なる時間を入力してください。');
            console.log('[FORM] 시작/종료 시간 동일, 등록 차단');
            return;
        }
    }
    
    // 警告メッセージを非表示
    hideFormWarning();
    
    // 実際の提出ロジック
    submitDailyData(formData);
}

// 選択された日付の月情報を確認
async function checkMonthlyDataForSelectedDate(selectedDate) {
    if (!selectedDate) {
        console.warn('[FORM] 선택된 날짜가 없습니다');
        return false;
    }
    
    try {
        // 日付形式の統一 (YYYY年M月D日 -> YYYY-MM-DD)
        let normalizedDate = selectedDate;
        if (selectedDate.includes('年') && selectedDate.includes('月')) {
            const match = selectedDate.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
            if (match) {
                const [, year, month, day] = match;
                normalizedDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
                console.log(`[FORM] 날짜 형식 변환: ${selectedDate} -> ${normalizedDate}`);
            }
        }
        
        const dateParts = normalizedDate.split('-');
        const year = dateParts[0];
        const month = dateParts[1];
        
        console.log(`[FORM] 선택된 날짜의 월 정보 확인: ${year}-${month}`);
        
        // monthly-info/section API를 사용하여 월정보 존재 여부 확인
        const url = `/attendance/monthly-info/section/?year=${year}&month=${month}`;
        const response = await fetchWithCsrf(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        console.log(`[FORM] API 응답 상태: ${response.status}`);
        
        if (response.ok) {
            const html = await response.text();
            
            // HTML 응답에서 월정보 섹션 존재 여부 확인
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            const monthlySection = tempDiv.querySelector('#monthly-info-section');
            const noDataPrompt = tempDiv.querySelector('.no-data-prompt');
            
            const hasMonthlyData = monthlySection !== null && noDataPrompt === null;
            
            console.log(`[FORM] 월 정보 확인 결과: ${hasMonthlyData}`, {
                monthlySectionExists: monthlySection !== null,
                noDataPromptExists: noDataPrompt !== null,
                hasMonthlyData: hasMonthlyData
            });
            
            return hasMonthlyData;
        } else {
            console.log(`[FORM] 월 정보 없음: ${year}-${month} (HTTP ${response.status})`);
            return false;
        }
        
    } catch (error) {
        console.error('[FORM] 월 정보 확인 중 오류:', error);
        return false;
    }
}

// 日次データの提出
async function submitDailyData(formData) {
    try {
        // FormDataをJSONに変換
        const jsonData = {};
        for (const [key, value] of formData.entries()) {
            jsonData[key] = value;
        }
        
        // 現在の選択日付から年、月、日を抽出
        console.log(`[FORM] currentState.selectedDate: ${currentState.selectedDate}`);
        if (currentState.selectedDate) {
            const dateParts = currentState.selectedDate.split('-');
            jsonData.year = dateParts[0];
            jsonData.month = dateParts[1];
            jsonData.day = dateParts[2];
            console.log(`[FORM] 날짜 정보 추출: year=${jsonData.year}, month=${jsonData.month}, day=${jsonData.day}`);
        } else {
            console.error('[FORM] currentState.selectedDate가 설정되지 않았습니다!');
            return;
        }
        
        console.log('[FORM] 전송할 데이터:', jsonData);
        console.log('[FORM] alternative_work_date1:', jsonData.alternative_work_date1);
        console.log('[FORM] alternative_work_date2:', jsonData.alternative_work_date2);
        console.log('[FORM] alternative_work_date3:', jsonData.alternative_work_date3);
        
        const response = await fetchWithCsrf('/attendance/daily/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(jsonData)
        });
        
        if (response.ok) {
            console.log('[FORM] データ提出成功');
            // 成功時にカレンダーを更新
            updateCalendarSection(currentState.calendarYear, currentState.calendarMonth);
            // 現在の選択日付のフォームも更新
            if (currentState.selectedDate) {
                updateFormSection(currentState.selectedDate);
            }
        } else {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Failed to submit data');
        }
    } catch (error) {
        console.error('[FORM] 提出エラー:', error);
        alert(`データの保存に失敗しました: ${error.message}`);
    }
}

// ===================== 탭 전환 관련 함수 =====================

// タブ切り替えハンドラ
async function handleTabSwitch(event) {
    event.preventDefault();
    const targetTab = event.currentTarget.id;
    const tabListBtn = document.getElementById('tab-list');
    if (targetTab === 'tab-list' && tabListBtn && tabListBtn.disabled) {
        // リストタブが無効なら何もしない
        return;
    }
    
    const isList = (targetTab === 'tab-list');
    localStorage.setItem('selectedTab', isList ? 'list' : 'calendar');
    
    // 現在の年月を取得
    const currentMonthDisplay = document.getElementById('current-month-display');
    if (!currentMonthDisplay) {
        console.error('[TAB] 현재 년월 정보를 찾을 수 없음');
        return;
    }
    
    const year = parseInt(currentMonthDisplay.dataset.year);
    const month = parseInt(currentMonthDisplay.dataset.month);
    
    if (!year || !month) {
        console.error('[TAB] 년월 정보가 유효하지 않음');
        return;
    }
    
    // toggleState는 null로 전달하여 서버가 월정보 유무에 따라 결정하도록 함
    const toggleState = null;
    const showListParam = isList ? '1' : '0';
    
    console.log(`[TAB] 탭 전환: ${isList ? 'list' : 'calendar'}`);
    
    // AJAXで全カレンダーセクションを再読み込み (サーバーで正しいタブ状態でレンダリング)
    await updateCalendarSection(year, month, showListParam, toggleState);
}

// ===================== イベント初期化関数 =====================

// Day Arrow 이벤트만 재바인딩 (간단한 해결책)
function rebindDayArrowEvents() {
    const dayArrowLeft = document.getElementById('day-arrow-left');
    const dayArrowRight = document.getElementById('day-arrow-right');
    
    if (dayArrowLeft) {
        dayArrowLeft.addEventListener('click', () => handleDayArrowClick('prev'));
    }
    if (dayArrowRight) {
        dayArrowRight.addEventListener('click', () => handleDayArrowClick('next'));
    }
    
    console.log('[FORM] Day Arrow 이벤트 재바인딩 완료');
}

// フォームイベント再バインド
function rebindFormEvents() {
    console.log('[FORM] イベント再バインド');
    
    // Day Arrow ボタン
    const dayArrowLeft = document.getElementById('day-arrow-left');
    const dayArrowRight = document.getElementById('day-arrow-right');
    
    if (dayArrowLeft) {
        dayArrowLeft.addEventListener('click', () => handleDayArrowClick('prev'));
    }
    if (dayArrowRight) {
        dayArrowRight.addEventListener('click', () => handleDayArrowClick('next'));
    }
    
    // 폼 제출 이벤트 및 근무구분 변경 이벤트
    const dailyForm = document.getElementById('daily-entry-form');
    if (dailyForm) {
        dailyForm.addEventListener('submit', handleFormSubmit);
        
        // 폼 요소들 한 번에 찾기 (중복 제거)
        const workTypeSelect = dailyForm.querySelector('[name="work_type"]');
        const startTimeInput = dailyForm.querySelector('[name="start_time"]');
        const endTimeInput = dailyForm.querySelector('[name="end_time"]');
        const normalHoursBtn = document.getElementById('normal-hours-btn');
        
        // 통상 버튼 이벤트
        if (normalHoursBtn) {
            normalHoursBtn.addEventListener('click', () => {
                console.log('[DEBUG] 통상 버튼 클릭됨');
                console.log('[DEBUG] normalHoursBtn.dataset:', normalHoursBtn.dataset);
                
                // 서버에서 전달된 시간 데이터 사용
                const startTime = normalHoursBtn.dataset.startTime;
                const endTime = normalHoursBtn.dataset.endTime;
                
                console.log('[DEBUG] startTime:', startTime, 'endTime:', endTime);
                console.log('[DEBUG] startTimeInput:', startTimeInput, 'endTimeInput:', endTimeInput);
                
                if (startTime && endTime) {
                    if (startTimeInput) {
                        startTimeInput.value = startTime;
                        console.log('[DEBUG] startTimeInput.value 설정됨:', startTimeInput.value);
                    }
                    if (endTimeInput) {
                        endTimeInput.value = endTime;
                        console.log('[DEBUG] endTimeInput.value 설정됨:', endTimeInput.value);
                    }
                    console.log(`[DEBUG] Normal hours set: ${startTime} - ${endTime}`);
                } else {
                    console.warn('[DEBUG] Normal hours data not available');
                    console.warn('[DEBUG] startTime:', startTime, 'endTime:', endTime);
                }
            });
        }
        
        // 근무구분 변경 이벤트
        if (workTypeSelect && startTimeInput && endTimeInput && normalHoursBtn) {
            console.log('[REBIND] 근무구분 변경 이벤트 재바인딩');
            
            // 기존 이벤트 리스너 제거 (중복 방지)
            workTypeSelect.removeEventListener('change', workTypeSelect._changeHandler);
            
            // 새 이벤트 핸들러 생성 및 등록
            workTypeSelect._changeHandler = function() {
                console.log('[EVENT] 근무구분 변경 이벤트 발생:', workTypeSelect.value);
                syncFormStateByWorkType(workTypeSelect.value, startTimeInput, endTimeInput, normalHoursBtn);
                
                // 현재 날짜 기준 옵션 필터링
                let dateStr = null;
                const dayInputHidden = document.getElementById('day-input-hidden');
                if (dayInputHidden) {
                    const y = currentState.calendarYear;
                    const m = String(currentState.calendarMonth).padStart(2, '0');
                    const d = String(dayInputHidden.value).padStart(2, '0');
                    dateStr = `${y}-${m}-${d}`;
                }
                if (dateStr) {
                    filterWorkTypeOptionsByDate(dateStr);
                }
                
                // 대체근무일 필드 토글
                toggleAltWorkDateField(workTypeSelect.value);
            };
            
            workTypeSelect.addEventListener('change', workTypeSelect._changeHandler);
        }
    }
    
    // ツールチップイベント再バインド
    setupWorkTypeTooltip();
    
    // 추가 버튼 이벤트 재바인딩
    initializeAdditionalDatesToggle();
    
    // カレンダーで日付選択時の勤務区分オプションフィルタリング適用
    if (currentState.selectedDate) {
        filterWorkTypeOptionsByDate(currentState.selectedDate);
    }
}

// フォームイベント初期化
function initializeFormEvents() {
    console.log('[INIT] フォームイベント初期化');
    
    // Day Arrow 버튼
    const dayArrowLeft = document.getElementById('day-arrow-left');
    const dayArrowRight = document.getElementById('day-arrow-right');
    
    if (dayArrowLeft) {
        dayArrowLeft.addEventListener('click', () => handleDayArrowClick('prev'));
    }
    if (dayArrowRight) {
        dayArrowRight.addEventListener('click', () => handleDayArrowClick('next'));
    }
    
    // 통상 버튼 이벤트 추가
    const normalHoursBtn = document.getElementById('normal-hours-btn');
    if (normalHoursBtn) {
        normalHoursBtn.addEventListener('click', () => {
            console.log('[DEBUG] 통상 버튼 클릭됨 (initializeFormEvents)');
            console.log('[DEBUG] normalHoursBtn.dataset:', normalHoursBtn.dataset);
            
            const startTimeInput = document.querySelector('[name="start_time"]');
            const endTimeInput = document.querySelector('[name="end_time"]');
            
            // 서버에서 전달된 시간 데이터 사용
            const startTime = normalHoursBtn.dataset.startTime;
            const endTime = normalHoursBtn.dataset.endTime;
            
            console.log('[DEBUG] startTime:', startTime, 'endTime:', endTime);
            console.log('[DEBUG] startTimeInput:', startTimeInput, 'endTimeInput:', endTimeInput);
            
            if (startTime && endTime) {
                if (startTimeInput) {
                    startTimeInput.value = startTime;
                    console.log('[DEBUG] startTimeInput.value 설정됨:', startTimeInput.value);
                }
                if (endTimeInput) {
                    endTimeInput.value = endTime;
                    console.log('[DEBUG] endTimeInput.value 설정됨:', endTimeInput.value);
                }
                console.log(`[DEBUG] Normal hours set: ${startTime} - ${endTime}`);
            } else {
                console.warn('[DEBUG] Normal hours data not available');
                console.warn('[DEBUG] startTime:', startTime, 'endTime:', endTime);
            }
        });
    }
    
    // 폼 제출 ##중복주의##
    const dailyForm = document.getElementById('daily-entry-form');
    console.log('[INIT] dailyForm 찾기:', dailyForm);
    if (dailyForm) {
        dailyForm.addEventListener('submit', handleFormSubmit);
        // 勤務区分 select 변경 시 폼 상태/옵션/필드 동기화
        const workTypeSelect = dailyForm.querySelector('[name="work_type"]');
        const startTimeInput = dailyForm.querySelector('[name="start_time"]');
        const endTimeInput = dailyForm.querySelector('[name="end_time"]');
        const normalHoursBtn = document.getElementById('normal-hours-btn');
        
        console.log('[INIT] 폼 요소들 찾기:', {
            workTypeSelect: workTypeSelect,
            startTimeInput: startTimeInput,
            endTimeInput: endTimeInput,
            normalHoursBtn: normalHoursBtn
        });
        
        if (workTypeSelect && startTimeInput && endTimeInput && normalHoursBtn) {
            console.log('[INIT] 근무구분 변경 이벤트 리스너 등록');
            workTypeSelect.addEventListener('change', function() {
                console.log('[EVENT] 근무구분 변경 이벤트 발생:', workTypeSelect.value);
                syncFormStateByWorkType(workTypeSelect.value, startTimeInput, endTimeInput, normalHoursBtn);
                // 현재 날짜 기준 옵션 필터링
                let dateStr = null;
                const dayInputHidden = document.getElementById('day-input-hidden');
                if (dayInputHidden) {
                    const y = currentYear;
                    const m = String(currentMonth).padStart(2, '0');
                    const d = String(dayInputHidden.value).padStart(2, '0');
                    dateStr = `${y}-${m}-${d}`;
                }
                if (dateStr) {
                    filterWorkTypeOptionsByDate(dateStr);
                }
                toggleAltWorkDateField(workTypeSelect.value);
            });
            // ページロード時にも状態反映/옵ション필터/필드표시
            syncFormStateByWorkType(workTypeSelect.value, startTimeInput, endTimeInput, normalHoursBtn);
            let dateStr = null;
            const dayInputHidden = document.getElementById('day-input-hidden');
            if (dayInputHidden) {
                const y = currentYear;
                const m = String(currentMonth).padStart(2, '0');
                const d = String(dayInputHidden.value).padStart(2, '0');
                dateStr = `${y}-${m}-${d}`;
            }
            if (dateStr) {
                filterWorkTypeOptionsByDate(dateStr);
            }
            toggleAltWorkDateField(workTypeSelect.value);
        } else {
            console.log('[INIT] 이벤트 등록 실패 - 일부 요소가 없음');
        }
    } else {
        console.log('[INIT] dailyForm을 찾을 수 없음');
    }
    
    // 로고 클릭 이벤트
    const logoLink = document.querySelector('.logo a');
    const techaveLogo = document.getElementById('techave-logo');
    if (logoLink) {
        logoLink.addEventListener('click', (e) => {
            e.preventDefault();
            goToToday();
        });
    }
    if (techaveLogo) {
        techaveLogo.addEventListener('click', (e) => {
            e.preventDefault();
            goToToday();
        });
    }
    
    // 설문조사 버튼 이벤트
    const surveyBtn = document.getElementById('survey-btn');
    console.log('[DEBUG] 설문조사 버튼 찾기:', surveyBtn);
    if (surveyBtn) {
        surveyBtn.addEventListener('click', (e) => {
            console.log('[DEBUG] 설문조사 버튼 클릭됨');
            openSurvey();
        });
        console.log('[DEBUG] 설문조사 버튼 이벤트 리스너 등록 완료');
    } else {
        console.warn('[DEBUG] 설문조사 버튼을 찾을 수 없습니다');
    }
}

// リストイベント初期化
function initializeListEvents() {
    console.log('[LIST] リス트イベント初期化開始');
    // 既存のイベントを削除
    document.removeEventListener('click', handleGlobalListClick);
    document.addEventListener('click', handleGlobalListClick);
    // 削除ボタンイベントの委譲
    document.removeEventListener('click', handleDeleteDailyClick);
    document.addEventListener('click', handleDeleteDailyClick);
    // リスト行の数を確認
    const listRows = document.querySelectorAll('.attendance-list-row');
    console.log(`[LIST] リスト行の数: ${listRows.length}`);
    
    // リストビュー祝日処理初期化
    initializeListViewHolidayHandling();
    
    console.log('[LIST] リストイベント初期化完了');
}

// グローバルリストクリックハンドラ (関数名で登録する必要があるため削除可能)
function handleGlobalListClick(event) {
    const listRow = event.target.closest('.attendance-list-row');
    if (listRow) {
        console.log('[LIST] 리스트 행 클릭 감지:', listRow);
        event.preventDefault();
        event.stopPropagation();
        handleListRowClick({ currentTarget: listRow });
    }
}

// 삭제 버튼 클릭 핸들러 (이벤트 위임)
function handleDeleteDailyClick(event) {
    const btn = event.target.closest('.delete-daily-btn');
    if (!btn) return;
    event.preventDefault();
    const dateStr = btn.getAttribute('data-date');
    if (!dateStr) return;
    if (!confirm('本当にこの日付の勤怠情報を削除しますか？')) return;
    fetch('/attendance/daily/delete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken,
        },
        body: JSON.stringify({ date: dateStr })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            // 삭제 성공 시 캘린더 갱신
            updateCalendarSection(currentState.calendarYear, currentState.calendarMonth);
            // 현재 선택된 날짜가 삭제된 날짜와 같다면 폼도 갱신
            if (currentState.selectedDate === dateStr) {
                updateFormSection(dateStr);
            }
        } else {
            alert(data.message || '削除に失敗しました。');
        }
    })
    .catch(err => {
        alert('削除リクエストに失敗しました: ' + err.message);
    });
}

// カレンダーイベント初期化
function initializeCalendarEvents() {
    console.log('[INIT] カレンダーイベント初期化');
    
    // 월 네비게이션
    const prevMonthBtn = document.getElementById('prev-month-btn');
    const nextMonthBtn = document.getElementById('next-month-btn');
    
    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', () => handleMonthNavigation('prev'));
    }
    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', () => handleMonthNavigation('next'));
    }
    
    // 캘린더 셀 (empty-cell과 other-month가 아닌 셀에만 이벤트 등록)
    const calendarCells = document.querySelectorAll('.calendar-table td');
    calendarCells.forEach(cell => {
        if (!cell.classList.contains('empty-cell') && !cell.classList.contains('other-month')) {
            const dateNumber = cell.querySelector('.date-number');
            if (dateNumber) {
                cell.addEventListener('click', handleCalendarCellClick);
            }
        }
    });
    
    // 리스트 행
    const listRows = document.querySelectorAll('.attendance-list-row');
    listRows.forEach(row => {
        row.addEventListener('click', handleListRowClick);
    });
    
    // 월/년 표시 클릭 시 모달 오픈
    const monthDisplay = document.getElementById('current-month-display');
    const pickerModal = document.getElementById('year-month-picker-modal');
    if (monthDisplay && pickerModal) {
        monthDisplay.style.cursor = 'pointer';
        // 기존 이벤트 제거 후 바인딩(중복 방지)
        monthDisplay.removeEventListener('click', handleMonthDisplayClick);
        monthDisplay.addEventListener('click', handleMonthDisplayClick);
    }
    
    // 月情報登録モーダル
    const createMonthlyBtn = document.getElementById('create-monthly-btn');
    if (createMonthlyBtn) {
        createMonthlyBtn.addEventListener('click', MonthlyModalModule.open);
    }
    const closeModalBtn = document.getElementById('close-modal-btn');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', MonthlyModalModule.close);
    }
    const monthlyForm = document.getElementById('monthly-form');
    if (monthlyForm) {
        monthlyForm.addEventListener('submit', MonthlyModalModule.submit);
    }
    MonthlyModalModule.bindEvents();

    // 월정보 수정 모달 관련 이벤트는 월정보가 로드된 후에 등록됨

    // 새로운 월정보 토글 버튼 이벤트 핸들러
    const monthlyInfoToggleBtn = document.getElementById('monthly-info-toggle-btn');
    if (monthlyInfoToggleBtn) {
        // 기존 이벤트 제거 후 새로 등록 (중복 방지)
        monthlyInfoToggleBtn.removeEventListener('click', handleMonthlyInfoToggle);
        monthlyInfoToggleBtn.addEventListener('click', handleMonthlyInfoToggle);
        console.log('[INIT] 월정보 토글 버튼 이벤트 등록 완료');
    }
    
    // 로그아웃 버튼 이벤트 핸들러
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            // localStorage에서 토글 상태 삭제
            localStorage.removeItem('monthlyInfoOpen');
            localStorage.removeItem('selectedTab');
        });
    }

    // 이전 월 복사 버튼 이벤트 핸들러
    const copyPrevMonthBtn = document.getElementById('copy-prev-month-btn');
    if (copyPrevMonthBtn) {
        copyPrevMonthBtn.removeEventListener('click', handleCopyPrevMonth);
        copyPrevMonthBtn.addEventListener('click', handleCopyPrevMonth);
    }



    console.log(`[INIT] カレンダーイベント完了 (셀: ${calendarCells.length}, 행: ${listRows.length})`);
}

// TTL 기반 캐시 사용 (5분 자동 만료)
// 페이지 로드 시 캐시 초기화는 더 이상 필요하지 않음

// 이전 월 복사 핸들러
async function handleCopyPrevMonth() {
    console.log('[COPY] 이전 월 복사 시작');
    
    try {
        const response = await fetchWithCsrf('/attendance/copy_prev_month/', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                year: currentState.calendarYear,
                month: currentState.calendarMonth
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('[COPY] 이전 월 복사 성공');
            alert('前月の情報が正常にコピーされました。');
            // 캘린더 섹션 새로고침
            await updateCalendarSection(currentState.calendarYear, currentState.calendarMonth);
            // 폼 섹션도 업데이트하여 비활성화 상태 해제
            if (currentState.selectedDate) {
                updateFormSection(currentState.selectedDate);
            }
        } else {
            console.error('[COPY] 이전 월 복사 실패:', data.message);
            alert('이전 월 복사에 실패했습니다: ' + data.message);
        }
    } catch (error) {
        console.error('[COPY] 이전 월 복사 오류:', error);
        alert('이전 월 복사 중 오류가 발생했습니다.');
    }
}





// 월/년 표시 클릭 핸들러(함수 분리)
function handleMonthDisplayClick() {
    const monthDisplay = document.getElementById('current-month-display');
    const pickerModal = document.getElementById('year-month-picker-modal');
    if (!monthDisplay || !pickerModal) return;
    let currentYear = parseInt(monthDisplay.dataset.year) || new Date().getFullYear();
    updateYearMonthPicker(currentYear);
    pickerModal.classList.add('show');

    // ========== 월 버튼 이벤트 바인딩(모달 열릴 때마다) ==========
    const monthGrid = document.querySelector('.month-grid');
    if (monthGrid) {
        const newMonthGrid = monthGrid.cloneNode(true);
        monthGrid.parentNode.replaceChild(newMonthGrid, monthGrid);
        newMonthGrid.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                const selectedMonth = e.target.dataset.month;
                currentState.calendarYear = currentYear;
                currentState.calendarMonth = parseInt(selectedMonth);
                updateCalendarSection(currentYear, parseInt(selectedMonth));
                pickerModal.classList.remove('show');
            }
        });
    }

    // ========== 년도 이동 버튼 이벤트 바인딩 ==========
    const pickerYearDisplay = document.getElementById('picker-year');
    const prevYearBtn = document.getElementById('prev-year-btn');
    const nextYearBtn = document.getElementById('next-year-btn');
    if (prevYearBtn && nextYearBtn && pickerYearDisplay) {
        // 기존 이벤트 제거
        prevYearBtn.replaceWith(prevYearBtn.cloneNode(true));
        nextYearBtn.replaceWith(nextYearBtn.cloneNode(true));
        const newPrevYearBtn = document.getElementById('prev-year-btn');
        const newNextYearBtn = document.getElementById('next-year-btn');
        newPrevYearBtn.addEventListener('click', () => {
            currentYear--;
            updateYearMonthPicker(currentYear);
            pickerYearDisplay.textContent = currentYear;
        });
        newNextYearBtn.addEventListener('click', () => {
            currentYear++;
            updateYearMonthPicker(currentYear);
            pickerYearDisplay.textContent = currentYear;
        });
    }

    // ========== 닫기 버튼 이벤트 바인딩 ==========
    const closePickerBtn = document.getElementById('close-picker-btn');
    if (closePickerBtn) {
        closePickerBtn.replaceWith(closePickerBtn.cloneNode(true));
        const newCloseBtn = document.getElementById('close-picker-btn');
        newCloseBtn.addEventListener('click', () => {
            pickerModal.classList.remove('show');
        });
    }
}

// ===================== 年月ピッカーを生成・更新 =====================
function updateYearMonthPicker(year) {
    const pickerYearDisplay = document.getElementById('picker-year');
    const monthGrid = document.querySelector('.month-grid');
    if (!pickerYearDisplay || !monthGrid) return;
    pickerYearDisplay.textContent = year;
    monthGrid.innerHTML = '';
    for (let i = 1; i <= 12; i++) {
        const monthBtn = document.createElement('button');
        monthBtn.textContent = `${i}月`;
        monthBtn.dataset.month = i;
        monthGrid.appendChild(monthBtn);
    }
}

// ===================== 휴일 표시 관련 함수 =====================

// 일본 공휴일 API에서 이번 달의 데이터를 추출해서 캘린더에 표시
    /**
     * 일본 공휴일 API 데이터를 캘린더에 적용
     * API에서 가져온 공휴일 정보를 해당 월의 캘린더 셀에 표시
     */
    async function applyApiHolidaysToCalendar() {
        console.log('[HOLIDAY API] 함수 시작');
        
        // window.apiHolidays 확인
        console.log('[HOLIDAY API] window.apiHolidays:', window.apiHolidays);
        console.log('[HOLIDAY API] window.apiHolidays 타입:', typeof window.apiHolidays);
        
        const apiHolidays = window.apiHolidays || {};
        const year = currentState.calendarYear || (new Date()).getFullYear();
        const month = currentState.calendarMonth || (new Date()).getMonth() + 1;
        const monthStr = String(month).padStart(2, '0');
        
        console.log(`[HOLIDAY API] ${year}년 ${month}월 공휴일 적용 시작`);
        console.log(`[HOLIDAY API] 전체 공휴일 데이터:`, apiHolidays);
        console.log(`[HOLIDAY API] 공휴일 데이터 개수:`, Object.keys(apiHolidays).length);
        
        let appliedCount = 0;
        
        // 해당 월의 공휴일만 필터링하여 적용
        Object.entries(apiHolidays).forEach(([date, holidayName]) => {
            console.log(`[HOLIDAY API] 검사 중: ${date} - ${holidayName}`);
            
            if (date.startsWith(`${year}-${monthStr}`)) {
                console.log(`[HOLIDAY API] 해당 월 공휴일 발견: ${date} - ${holidayName}`);
                
                const td = document.querySelector(`.calendar-table td[data-date='${date}']`);
                console.log(`[HOLIDAY API] 찾은 셀:`, td);
                
                if (td) {
                    applyHolidayToCell(td, holidayName, 'api');
                    appliedCount++;
                    console.log(`[HOLIDAY API] 공휴일 적용: ${date} - ${holidayName}`);
                } else {
                    console.warn(`[HOLIDAY API] 셀을 찾을 수 없음: ${date}`);
                }
            }
        });
        
        console.log(`[HOLIDAY API] 적용 완료: ${appliedCount}개 공휴일 적용됨`);
    }

    /**
     * DB holidays_db에서 공통/개별(calendar_name) 공휴일을 캘린더에 표시
     * 데이터베이스에 저장된 공휴일 정보를 캘린더 셀에 적용
     */
    function applyDbHolidaysToCalendar() {
        let holidaysDb = {};
        
        try {
            const holidaysScript = document.getElementById('holidays-db-data');
            if (holidaysScript) {
                holidaysDb = JSON.parse(holidaysScript.textContent);
            }
        } catch (e) {
            console.error('[HOLIDAY DB] holidays_db 파싱 에러:', e);
            return;
        }
        
        console.log('[HOLIDAY DB] DB 공휴일 데이터:', holidaysDb);
        
        const tds = document.querySelectorAll('.calendar-table td[data-date]');
        let appliedCount = 0;
        
        tds.forEach(td => {
            const dateStr = td.getAttribute('data-date');
            
            if (holidaysDb[dateStr]) {
                holidaysDb[dateStr].forEach(holiday => {
                    let type = 'db';
                    
                    // 공휴일 타입에 따른 클래스명 결정
                    if (holiday.calendar_name === '共通') {
                        type += ' common';
                    } else if (holiday.category && holiday.category.includes('年休収得')) {
                        type += ' green';
                    } else {
                        type += ' base';
                    }
                    
                    applyHolidayToCell(td, holiday.category, type);
                    appliedCount++;
                });
            }
        });
        
        console.log(`[HOLIDAY DB] 적용 완료: ${appliedCount}개 DB 공휴일 적용됨`);
    }

    /**
     * 공휴일 정보를 캘린더 셀에 적용
     * @param {HTMLElement} td - 캘린더 셀 요소
     * @param {string} holidayName - 공휴일 명칭
     * @param {string} type - 공휴일 타입 ('api', 'db', 'common', 'base', 'green')
     */
    function applyHolidayToCell(td, holidayName, type) {
        console.log(`[HOLIDAY CELL] applyHolidayToCell 호출:`, { holidayName, type });
        console.log(`[HOLIDAY CELL] td 요소:`, td);
        
        // holiday-category 요소 찾기 또는 생성
        let holidayCategory = td.querySelector('.holiday-category');
        console.log(`[HOLIDAY CELL] 기존 holiday-category:`, holidayCategory);
        
        if (!holidayCategory) {
            const cellHeader = td.querySelector('.cell-header');
            console.log(`[HOLIDAY CELL] cell-header:`, cellHeader);
            
            if (!cellHeader) {
                console.warn('[HOLIDAY CELL] cell-header를 찾을 수 없음');
                return;
            }
            holidayCategory = document.createElement('span');
            holidayCategory.className = 'holiday-category';
            cellHeader.appendChild(holidayCategory);
            console.log(`[HOLIDAY CELL] holiday-category 생성됨:`, holidayCategory);
        }
        
        // 기존 공휴일 요소 제거 (중복 방지)
        const existingItems = holidayCategory.querySelectorAll('.holiday-cat-item');
        console.log(`[HOLIDAY CELL] 기존 공휴일 요소 개수:`, existingItems.length);
        
        existingItems.forEach(item => {
            if (item.classList.contains(type)) {
                item.remove();
                console.log(`[HOLIDAY CELL] 기존 요소 제거:`, item);
            }
        });
        
        // 새로운 공휴일 요소 생성
        const holidaySpan = document.createElement('span');
        holidaySpan.className = `holiday-cat-item ${type}`;
        holidaySpan.textContent = holidayName;
        holidayCategory.appendChild(holidaySpan);
        console.log(`[HOLIDAY CELL] 새 공휴일 요소 생성:`, holidaySpan.outerHTML);
        
        // 날짜 숫자에 holiday 클래스 추가 (빨간색 표시)
        const dateNumber = td.querySelector('.date-number');
        console.log(`[HOLIDAY CELL] date-number:`, dateNumber);
        
        if (dateNumber && !dateNumber.classList.contains('holiday')) {
            dateNumber.classList.add('holiday');
            console.log(`[HOLIDAY CELL] date-number에 holiday 클래스 추가됨`);
        }
        
        console.log(`[HOLIDAY CELL] 공휴일 적용 완료: ${holidayName} (${type})`);
    }
    
    /**
     * 기존 appendHolidayToCell 함수 (호환성 유지)
     * @deprecated applyHolidayToCell 함수 사용 권장
     */
    function appendHolidayToCell(td, text, className) {
        applyHolidayToCell(td, text, className);
    }

    /**
     * 모든 공휴일 표시 (초기화 포함)
     * API 공휴일과 DB 공휴일을 모두 캘린더에 적용
     */
    async function applyAllHolidaysToCalendar() {
        console.log('[HOLIDAY] ==========================================');
        console.log('[HOLIDAY] 모든 공휴일 적용 시작');
        console.log('[HOLIDAY] 현재 상태:', { 
            calendarYear: currentState.calendarYear, 
            calendarMonth: currentState.calendarMonth 
        });
        
        // 1. 기존 공휴일 표시 초기화
        console.log('[HOLIDAY] 1단계: 기존 공휴일 초기화');
        clearAllHolidaysFromCalendar();
        
        // 2. API 공휴일 적용
        console.log('[HOLIDAY] 2단계: API 공휴일 적용');
        await applyApiHolidaysToCalendar();
        
        // 3. DB 공휴일 적용
        console.log('[HOLIDAY] 3단계: DB 공휴일 적용');
        applyDbHolidaysToCalendar();
        
            console.log('[HOLIDAY] 모든 공휴일 적용 완료');
    console.log('[HOLIDAY] ==========================================');
}

// ===================== リストビュー祝日処理モジュール =====================

/**
 * リストビューで祝日の日付と曜日を赤色で表示
 * 祝日の行にholidayクラスを追加してCSSで赤色表示
 */
function applyHolidayStylesToListView() {
    console.log('[LIST HOLIDAY] リストビュー祝日スタイル適用開始');
    
    const listRows = document.querySelectorAll('.attendance-list-row');
    let appliedCount = 0;
    
    listRows.forEach(row => {
        const dateStr = row.dataset.date;
        if (!dateStr) return;
        
        // 백엔드에서 설정된 is_api_holiday 확인
        const isApiHoliday = row.dataset.isApiHoliday === 'true';
        const holidayType = getHolidayTypeByDate(dateStr);
        
        console.log(`[LIST HOLIDAY] ${dateStr}: isApiHoliday=${isApiHoliday}, holidayType=${holidayType}`);
        
        if (isApiHoliday || holidayType === '祝日') {
            // 祝日の行にholidayクラスを追加
            row.classList.add('holiday');
            
            // 日付と曜日セルにholidayクラスを追加
            const dateCell = row.querySelector('.date-col');
            const weekdayCell = row.querySelector('.weekday-col');
            
            if (dateCell) dateCell.classList.add('holiday');
            if (weekdayCell) weekdayCell.classList.add('holiday');
            
            appliedCount++;
            console.log(`[LIST HOLIDAY] 祝日スタイル 적용: ${dateStr}`);
        }
    });
    
    console.log(`[LIST HOLIDAY] 祝日スタイル適用完了: ${appliedCount}行`);
}

/**
 * リストビューの祝日行クリック時に祝日を自動設定
 * データがない場合、勤務区分に「祝日」を自動入力
 */
function setupHolidayListRowClick() {
    console.log('[LIST HOLIDAY] 祝日行クリック処理設定');
    
    const listRows = document.querySelectorAll('.attendance-list-row');
    
    listRows.forEach(row => {
        const dateStr = row.dataset.date;
        if (!dateStr) return;
        
        const holidayType = getHolidayTypeByDate(dateStr);
        if (holidayType === '祝日') {
            // 祝日行に特別なクリック 이벤트 추가
            row.addEventListener('click', function(event) {
                console.log(`[LIST HOLIDAY] 祝日行クリック: ${dateStr}`);
                
                // 기존 리스트 행 클릭 처리 실행
                handleListRowClick({ currentTarget: row });
                
                // データがない 경우、勤務区分に「祝日」を自動設定
                const hasRecord = row.dataset.hasRecord === '1';
                if (!hasRecord) {
                    const workTypeSelect = document.querySelector('select[name="work_type"]');
                    if (workTypeSelect) {
                        workTypeSelect.value = '祝日';
                        console.log(`[LIST HOLIDAY] 勤務区分に「祝日」自動設定: ${dateStr}`);
                    }
                }
            });
        }
    });
}

/**
 * リストビュー祝日処理を初期化
 * スタイル適用とクリック 이벤트 설정
 */
function initializeListViewHolidayHandling() {
    console.log('[LIST HOLIDAY] リストビュー祝日処理初期化');
    
    // 祝日スタイル 적용
    applyHolidayStylesToListView();
    
    // 祝日行クリック 이벤트 설정
    setupHolidayListRowClick();
}
    
    /**
     * 캘린더에서 모든 공휴일 표시를 초기화
     */
    function clearAllHolidaysFromCalendar() {
        const tds = document.querySelectorAll('.calendar-table td[data-date]');
        
        tds.forEach(td => {
            // holiday-category 내의 모든 공휴일 요소 제거
            const holidayCategory = td.querySelector('.holiday-category');
            if (holidayCategory) {
                holidayCategory.querySelectorAll('.holiday-cat-item').forEach(item => item.remove());
            }
            
            // date-number에서 holiday 클래스 제거
            const dateNumber = td.querySelector('.date-number');
            if (dateNumber) {
                dateNumber.classList.remove('holiday');
            }
        });
        
        console.log('[HOLIDAY] 공휴일 표시 초기화 완료');
    }

// ===================== 印刷プレビューボタン関連ロジック =====================

/**
 * 印刷プレビューボタンのクリックイベントを初期化する
 * - ボタン押下時、現在の年月でPDFプレビューをモーダル表示
 * - 必要な要素がなければ警告を出す
 */
function setupPrintPreviewLogic() {
    // 印刷プレビューボタン取得
    const printPreviewBtn = document.getElementById('print-preview-btn');
    if (!printPreviewBtn) {
        console.warn('[PRINT] print-preview-btnが見つかりません');
        return;
    }
    printPreviewBtn.addEventListener('click', function() {
        // 年月情報取得
        const currentMonthDisplay = document.getElementById('current-month-display');
        if (!currentMonthDisplay) {
            alert('現在の年月情報が取得できません');
            return;
        }
        const year = currentMonthDisplay.dataset.year;
        const month = currentMonthDisplay.dataset.month;
        if (!year || !month) {
            alert('年または月の情報がありません');
            return;
        }
        // PDFプレビューURL生成
        const pdfUrl = `/pdf/preview/?year=${year}&month=${month}`;
        // PDF iframeにURLを設定
        const pdfIframe = document.getElementById('pdf-iframe');
        if (pdfIframe) {
            pdfIframe.src = pdfUrl;
        } else {
            alert('PDFプレビュー用のiframeが見つかりません');
            return;
        }
        // モーダル表示
        const pdfModal = document.getElementById('pdf-preview-modal');
        if (pdfModal) {
            pdfModal.classList.add('show');
        } else {
            alert('PDFプレビューモーダルが見つかりません');
        }
    });

    // ===================== モーダル内ボタンのイベント登録 =====================
    setupPdfModalButtons();
}

/**
 * PDFプレビューモーダル内の各ボタンイベントを初期化
 */
function setupPdfModalButtons() {
    // 閉じるボタン
    const closeBtn = document.getElementById('close-pdf-modal-btn');
    if (closeBtn) {
        closeBtn.removeEventListener('click', closeBtn._closeHandler);
        closeBtn._closeHandler = function() {
            const pdfModal = document.getElementById('pdf-preview-modal');
            if (pdfModal) pdfModal.classList.remove('show');
            const pdfIframe = document.getElementById('pdf-iframe');
            if (pdfIframe) pdfIframe.src = '';
        };
        closeBtn.addEventListener('click', closeBtn._closeHandler);
    }
    // 印刷ボタン
    const printBtn = document.getElementById('print-pdf-btn');
    if (printBtn) {
        printBtn.removeEventListener('click', printBtn._printHandler);
        printBtn._printHandler = function() {
            const iframe = document.getElementById('pdf-iframe');
            if (iframe && iframe.contentWindow) iframe.contentWindow.print();
        };
        printBtn.addEventListener('click', printBtn._printHandler);
    }
    // PDF保存ボタン
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    if (downloadPdfBtn) {
        downloadPdfBtn.removeEventListener('click', downloadPdfBtn._downloadPdfHandler);
        downloadPdfBtn._downloadPdfHandler = function() {
            const currentMonthDisplay = document.getElementById('current-month-display');
            if (!currentMonthDisplay) return;
            const year = currentMonthDisplay.dataset.year;
            const month = currentMonthDisplay.dataset.month;
            const pdfUrl = `/pdf/preview/?year=${year}&month=${month}`;
            const link = document.createElement('a');
            link.href = pdfUrl;
            link.download = `${year}_${month}_稼動報告書_.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
        downloadPdfBtn.addEventListener('click', downloadPdfBtn._downloadPdfHandler);
    }
    // Excel保存ボタン
    const downloadExcelBtn = document.getElementById('download-excel-btn');
    if (downloadExcelBtn) {
        downloadExcelBtn.removeEventListener('click', downloadExcelBtn._downloadExcelHandler);
        downloadExcelBtn._downloadExcelHandler = function() {
            const currentMonthDisplay = document.getElementById('current-month-display');
            if (!currentMonthDisplay) return;
            const year = currentMonthDisplay.dataset.year;
            const month = currentMonthDisplay.dataset.month;
            const excelUrl = `/excel/download/?year=${year}&month=${month}`;
            const link = document.createElement('a');
            link.href = excelUrl;
            link.download = `${year}_${month}_稼動報告書_.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
        downloadExcelBtn.addEventListener('click', downloadExcelBtn._downloadExcelHandler);
    }
}

// ===================== 애플리케이션 초기화 =====================

// ==========================================　//
function setupEmailSelectLogic() {
    const emailToSelect = document.getElementById('email-to-select');
    const emailInput = document.getElementById('email-to');
    if (emailToSelect && emailInput) {
        let candidatesLoaded = false;
        emailToSelect.addEventListener('focus', function() {
            if (candidatesLoaded) return;
            fetch('/attendance/api/email_candidates/', { credentials: 'same-origin' })
                .then(res => {
                    if (!res.ok) throw new Error('ネットワークエラー');
                    return res.json();
                })
                .then(data => {
                    if (data.candidates) {
                        // 既存の候補をクリア（直接入力以外）
                        for (let i = emailToSelect.options.length - 1; i >= 0; i--) {
                            if (emailToSelect.options[i].value !== '__manual__' && emailToSelect.options[i].value !== '') {
                                emailToSelect.remove(i);
                            }
                        }
                        data.candidates.forEach(c => {
                            const opt = document.createElement('option');
                            opt.value = c.email;
                            opt.textContent = `${c.display_name} (${c.email})`;
                            emailToSelect.appendChild(opt);
                        });
                        candidatesLoaded = true;
                    } else {
                        // 候補がない場合
                        const opt = document.createElement('option');
                        opt.value = '';
                        opt.textContent = '候補者なし';
                        emailToSelect.appendChild(opt);
                    }
                })
                .catch(err => {
                    // ネットワークエラー等
                    alert('メール候補の取得に失敗しました: ' + err.message);
                });
        });
        emailToSelect.addEventListener('change', function() {
            if (emailToSelect.value === '__manual__') {
                emailInput.value = '';
                emailInput.readOnly = false;
                emailInput.style.display = 'block';
                emailInput.focus();
            } else {
                emailInput.value = emailToSelect.value;
                emailInput.readOnly = true;
                emailInput.style.display = 'none';
            }
        });
    }
}

// ===================== メール送信 + ファイル選択モーダルロジック =====================
let pendingEmail = '';
let pendingHostUser = '';
let pendingHostPassword = '';

function setupEmailSendLogic() {
    const emailForm = document.getElementById('email-send-form');
    const emailInput = document.getElementById('email-to');
    const emailHostUserInput = document.getElementById('email-host-user');
    const emailHostPasswordInput = document.getElementById('email-host-password');
    const fileTypeModal = document.getElementById('file-type-modal');
    
    // メールフィールドの初期化関数
    function clearEmailFields() {
        if (emailHostUserInput) emailHostUserInput.value = '';
        if (emailHostPasswordInput) emailHostPasswordInput.value = '';
        if (emailInput) emailInput.value = '';
        const emailToSelect = document.getElementById('email-to-select');
        if (emailToSelect) emailToSelect.value = '';
    }
    
    // ページ読み込み時にメールフィールドを初期化
    clearEmailFields();
    
    // メールフォームの送信イベントを設定
    if (emailForm && emailInput && fileTypeModal) {
        emailForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = emailInput.value.trim();
            const hostUser = emailHostUserInput ? emailHostUserInput.value.trim() : '';
            const hostPassword = emailHostPasswordInput ? emailHostPasswordInput.value.trim() : '';
            if (!email) return; // メールアドレスが空の場合は何もしない
            // 送信中のメール情報を保存
            pendingEmail = email;
            pendingHostUser = hostUser;
            pendingHostPassword = hostPassword;
            // ファイル選択モーダルを表示
            fileTypeModal.classList.add('show');
        });
    }
}

// メール送信ステータスメッセージの表示
function showEmailStatus(msg, isError=false) {
    const emailStatus = document.getElementById('email-status-message');
    if (emailStatus) {
        emailStatus.textContent = msg;
        emailStatus.style.display = 'block';
        emailStatus.style.color = isError ? '#dc3545' : '#007bff';
        setTimeout(() => { emailStatus.style.display = 'none'; }, 4000);
    }
}

// メール送信リクエスト
async function sendMailRequest(fileType) {
    if (!pendingEmail) return; // 送信中のメールアドレスがない場合は何もしない
    const year = document.getElementById('current-month-display').dataset.year;
    const month = document.getElementById('current-month-display').dataset.month;
    showEmailStatus('送信中...', false);
    try {
        // タイムアウト設定
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2分 타임아웃
        
        const response = await fetch('/attendance/email/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                email: pendingEmail,
                file_type: fileType,
                year: year,
                month: month,
                email_host_user: pendingHostUser,
                email_host_password: pendingHostPassword
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        const result = await response.json();
        if (result.status === 'success') {
            // 메시지가 있으면 그것을 표시, 없으면 기본 메시지
            const message = result.message || 'メールが正常に送信されました！';
            showEmailStatus(message, false);
        } else {
            showEmailStatus(result.message || '送信に失敗しました。', true);
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            showEmailStatus('送信がタイムアウトしました。ファイルサイズが大きいか、ネットワークが不安定です。', true);
        } else {
            showEmailStatus('送信中にエラーが発生しました。', true);
        }
        console.error('Email send error:', err);
    }
    const fileTypeModal = document.getElementById('file-type-modal');
    if (fileTypeModal) fileTypeModal.classList.remove('show');
    pendingEmail = '';
    pendingHostUser = '';
    pendingHostPassword = '';
}

function setupFileTypeModalEvents() {
    const sendPdfBtn = document.getElementById('send-pdf-btn');
    const sendExcelBtn = document.getElementById('send-excel-btn');
    const closeFileTypeModalBtn = document.getElementById('close-file-type-modal-btn');
    const fileTypeModal = document.getElementById('file-type-modal');
    
    //PDFファイルの送信ボタン
    if (sendPdfBtn) {
        sendPdfBtn.removeEventListener('click', sendPdfBtn._pdfHandler);
        sendPdfBtn._pdfHandler = function() { sendMailRequest('pdf'); };
        sendPdfBtn.addEventListener('click', sendPdfBtn._pdfHandler);
    }
    //Excelファイルの送信ボタン
    if (sendExcelBtn) {
        sendExcelBtn.removeEventListener('click', sendExcelBtn._excelHandler);
        sendExcelBtn._excelHandler = function() { sendMailRequest('excel'); };
        sendExcelBtn.addEventListener('click', sendExcelBtn._excelHandler);
    }
    //モーダルの閉じるボタン
    if (closeFileTypeModalBtn && fileTypeModal) {
        closeFileTypeModalBtn.removeEventListener('click', closeFileTypeModalBtn._closeHandler);
        closeFileTypeModalBtn._closeHandler = function() {
            fileTypeModal.classList.remove('show');
        };
        closeFileTypeModalBtn.addEventListener('click', closeFileTypeModalBtn._closeHandler);
    }
}

// ===================== 代休/振替の勤務日追加ボタン機能 =====================
function initializeAdditionalDatesToggle() {
    console.log('[DEBUG] initializeAdditionalDatesToggle 시작');
    const toggleBtn = document.getElementById('toggle-additional-dates');
    const additionalDates = document.getElementById('additional-alt-dates');
    
    console.log('[DEBUG] toggleBtn:', toggleBtn);
    console.log('[DEBUG] additionalDates:', additionalDates);
    
    if (toggleBtn && additionalDates) {
        console.log('[DEBUG] 이벤트 리스너 추가');
        toggleBtn.addEventListener('click', function() {
            console.log('[DEBUG] 추가 버튼 클릭됨');
            const isVisible = additionalDates.style.display !== 'none';
            console.log('[DEBUG] 현재 표시 상태:', isVisible);
            
            if (isVisible) {
                additionalDates.style.display = 'none';
                toggleBtn.innerHTML = '<i class="fa-solid fa-plus"></i> 追加';
                console.log('[DEBUG] 숨김 처리');
            } else {
                additionalDates.style.display = 'block';
                toggleBtn.innerHTML = '<i class="fa-solid fa-minus"></i> 閉じる';
                console.log('[DEBUG] 표시 처리');
            }
        });
    } else {
        console.log('[DEBUG] 요소를 찾을 수 없음 - toggleBtn:', !!toggleBtn, 'additionalDates:', !!additionalDates);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('[APP] アプリケーション初期化開始');
    
    // 状態の初期化
    initializeState();
    
    // イベントの初期化
    initializeFormEvents();
    
    // 代休/振替の勤務日追加ボタン初期化
    initializeAdditionalDatesToggle();
    initializeCalendarEvents();
    initializeListEvents(); // リストイベントの初期化
    initializeTabSwitching(true); // タブ切り替えの初期化 (状態の復元を含む)
    setupEmailSelectLogic(); // 受信者メールセレクト+直接入력ロジックの初期化
    
    // 초기 폼 상태는 서버에서 이미 처리되므로 생략
    // 날짜 변경 시에만 updateMonthlyDataWarning() 호출됨
    setupEmailSendLogic(); // メール送信ロジックの初期化
    setupFileTypeModalEvents(); // ファイル選択モーダルイベントの初期化
    setupOvertimeTooltip(); // 残業時間ツールチップの初期化
    setupWorkTypeTooltip(); // 勤務区分ツールチップの初期化
    setupPrintPreviewLogic(); // 印刷プレビューボタンの初期化
    
    // 初期設定 (一度だけ実行)
    setTimeout(() => {
        applyAllHolidaysToCalendar();
        
        // 初期選択された日付があればハイライト
        if (currentState.selectedDate) {
            updateCalendarHighlight();
        }
        MonthlyInfoToggle.init(); // 月情報トグル状態の復元と表示
    }, 500);
    
    updateCalendarSection(currentYear, currentMonth); // 最初の入力時にもajaxでカレンダーを読み込む
    console.log('[APP] アプリケーション初期化完了');
});

// 탭 전환 초기화
function initializeTabSwitching(shouldRestoreState = false) {
    console.log('[INIT] タブ切り替え初期化', shouldRestoreState ? '(상태 복원 포함)' : '(이벤트만 재등록)');
    
    const tabCalendarBtn = document.getElementById('tab-calendar');
    const tabListBtn = document.getElementById('tab-list');
    
    if (tabCalendarBtn && tabListBtn) {
        // 기존 이벤트 제거 후 재등록 (중복 방지)
        tabCalendarBtn.removeEventListener('click', handleTabSwitch);
        tabListBtn.removeEventListener('click', handleTabSwitch);
        
        tabCalendarBtn.addEventListener('click', handleTabSwitch);
        tabListBtn.addEventListener('click', handleTabSwitch);
        console.log('[INIT] 탭 버튼 이벤트 등록 완료');
        
        // URL 파라미터 기반 렌더링이므로 탭 상태 복원 불필요
        } else {
        console.warn('[INIT] 탭 버튼을 찾을 수 없습니다');
    }
    
    console.log('[INIT] タブ切り替え初期化完료');
}

// ===================== 月情報登録モーダル関連 =====================
const MonthlyModalModule = {
    open: function() {
        const modal = document.getElementById('monthly-modal');
        if (modal) modal.classList.add('show');
        // 年月の初期値を必要に応じて設定
        // const year = currentState.calendarYear || new Date().getFullYear();
        // const month = currentState.calendarMonth || (new Date().getMonth() + 1);
        // 必要ならhidden input等にセット
    },
    close: function() {
        const modal = document.getElementById('monthly-modal');
        if (modal) modal.classList.remove('show');
    },
    submit: async function(e) {
        e.preventDefault();
        const form = document.getElementById('monthly-form');
        const formData = new FormData(form);
        // 年月情報を追加
        formData.append('year', currentState.calendarYear);
        formData.append('month', currentState.calendarMonth);
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await response.json();
            if (data.status === 'success') {
                MonthlyModalModule.close();
                // カレンダー/월情報 partialを更新
                updateCalendarSection(currentState.calendarYear, currentState.calendarMonth);
                // 폼 섹션도 업데이트하여 비활성화 상태 해제
                if (currentState.selectedDate) {
                    updateFormSection(currentState.selectedDate);
                }
            } else {
                alert(data.message || '登録に失敗しました');
            }
        } catch (err) {
            alert('通信エラー: ' + err.message);
        }
    },
    bindEvents: function() {
        // 登録ボタン
        const openBtn = document.getElementById('create-monthly-btn');
        if (openBtn) {
            openBtn.removeEventListener('click', MonthlyModalModule.open);
            openBtn.addEventListener('click', MonthlyModalModule.open);
        }
        // 閉じるボタン
        const closeBtn = document.getElementById('close-modal-btn');
        if (closeBtn) {
            closeBtn.removeEventListener('click', MonthlyModalModule.close);
            closeBtn.addEventListener('click', MonthlyModalModule.close);
        }
        // フォーム送信
        const form = document.getElementById('monthly-form');
        if (form) {
            form.removeEventListener('submit', MonthlyModalModule.submit);
            form.addEventListener('submit', MonthlyModalModule.submit);
        }
    }
};

// 月情報修正モーダル関連
const MonthlyUpdateModalModule = {
    open: function() {
        const modal = document.getElementById('monthly-update-modal');
        if (modal) modal.classList.add('show');
        
        // ====== 월정보 상세 패널에서 값 추출 ======
        const projectNameInput = document.getElementById('update-project-name');
        const baseCalendarInput = document.getElementById('update-base-calendar');
        const lunchBreakInput = document.getElementById('update-lunch-break');
        const standardTimeInput = document.getElementById('update-standard-time');
        
        // 상세정보 패널에서 strong 태그들 추출
        const detailStrongs = document.querySelectorAll('.monthly-details-grid .monthly-info-item strong.value');
        if (detailStrongs.length >= 4) {
            if (projectNameInput) projectNameInput.value = detailStrongs[0].textContent.trim();
            
            // calendar_id는 data-calendar-id 속성에서 ID를 직접 가져오기
            const calendarElement = detailStrongs[1];
            const calendarId = calendarElement.getAttribute('data-calendar-id');
            console.log(`[MONTHLY_UPDATE] 찾는 Calendar ID: "${calendarId}"`);
            
            if (baseCalendarInput && calendarId) {
                // ID로 직접 설정
                baseCalendarInput.value = calendarId;
                console.log(`[MONTHLY_UPDATE] Calendar 설정: ID ${calendarId}`);
            } else if (baseCalendarInput) {
                // ID가 없는 경우 기존 로직 사용 (calendar_name으로 찾기)
                const calendarName = detailStrongs[1].textContent.trim().replace(/\s*\(ID:\s*\d+\)\s*$/, '');
                console.log(`[MONTHLY_UPDATE] 찾는 Calendar 이름: "${calendarName}"`);
                
                const options = baseCalendarInput.querySelectorAll('option');
                let foundCalendarId = null;
                
                console.log(`[MONTHLY_UPDATE] 사용 가능한 Calendar 옵션들:`);
                for (let option of options) {
                    console.log(`  - "${option.textContent.trim()}" (ID: ${option.value})`);
                    if (option.textContent.trim() === calendarName) {
                        foundCalendarId = option.value;
                        break;
                    }
                }
                
                if (foundCalendarId) {
                    baseCalendarInput.value = foundCalendarId;
                    console.log(`[MONTHLY_UPDATE] Calendar 설정: ${calendarName} (ID: ${foundCalendarId})`);
                } else {
                    console.warn(`[MONTHLY_UPDATE] Calendar를 찾을 수 없음: "${calendarName}"`);
                    // 첫 번째 옵션을 기본값으로 설정
                    if (options.length > 0) {
                        baseCalendarInput.value = options[0].value;
                        console.log(`[MONTHLY_UPDATE] 기본값으로 설정: ${options[0].textContent.trim()} (ID: ${options[0].value})`);
                    }
                }
            }
            
            if (lunchBreakInput) lunchBreakInput.value = detailStrongs[2].textContent.replace(/[^0-9.]/g, '');
            if (standardTimeInput) standardTimeInput.value = detailStrongs[3].textContent.replace(/[^0-9.]/g, '');
        }
        
        // 필드 연동 로직도 여기서 호출
        bindMonthlyUpdateModalFieldLogic();
    },
    close: function() {
        const modal = document.getElementById('monthly-update-modal');
        if (modal) modal.classList.remove('show');
    },
    submit: async function(e) {
        e.preventDefault();
        const form = document.getElementById('monthly-update-form');
        const formData = new FormData(form);
        
        // 年月情報を追加
        formData.append('year', currentState.calendarYear);
        formData.append('month', currentState.calendarMonth);
        
        // readonly 필드의 값이 제대로 전송되도록 강제로 추가
        const lunchBreak = document.getElementById('update-lunch-break');
        const standardTime = document.getElementById('update-standard-time');
        if (lunchBreak && standardTime) {
            formData.set('break_minutes', lunchBreak.value);
            formData.set('standard_work_hours', standardTime.value);
        }
        
        try {
            const response = await fetch('/attendance/monthly/update/', {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (e) {
                alert('サーバーから正しいJSONが返されませんでした:\n' + (text || '[응답이ビ어있음]'));
                return false;
            }
            if (data.status === 'success') {
                MonthlyUpdateModalModule.close();
                updateCalendarSection(currentState.calendarYear, currentState.calendarMonth);
                // 폼 섹션도 업데이트하여 비활성화 상태 해제 및 통상 버튼 시간 업데이트
                if (currentState.selectedDate) {
                    updateFormSection(currentState.selectedDate);
                }
            } else {
                alert(data.message || '修正に失敗しました');
            }
        } catch (err) {
            alert('通信エラー: ' + err.message);
        }
        return false; // 폼의 기본 submit 동작을 완전히 차단
    },
    bindEvents: function() {
        // 修正ボタン
        const openBtn = document.getElementById('edit-monthly-btn');
        if (openBtn) {
            openBtn.removeEventListener('click', MonthlyUpdateModalModule.open);
            openBtn.addEventListener('click', MonthlyUpdateModalModule.open);
        }
        // 閉じるボタン
        const closeBtn = document.getElementById('close-update-modal-btn');
        if (closeBtn) {
            closeBtn.removeEventListener('click', MonthlyUpdateModalModule.close);
            closeBtn.addEventListener('click', MonthlyUpdateModalModule.close);
        }
        // フォーム送信
        const form = document.getElementById('monthly-update-form');
        if (form) {
            form.removeEventListener('submit', MonthlyUpdateModalModule.submit);
            form.addEventListener('submit', MonthlyUpdateModalModule.submit);
        }
        // フィールド連動
        bindMonthlyUpdateModalFieldLogic();
    }
};

// フィールド連動関数
function bindMonthlyUpdateModalFieldLogic() {
    const baseCalendar = document.getElementById('update-base-calendar');
    const lunchBreak = document.getElementById('update-lunch-break');
    const standardTime = document.getElementById('update-standard-time');
    if (baseCalendar && lunchBreak && standardTime) {
        baseCalendar.addEventListener('change', function() {
            const selectedOption = $(baseCalendar).find('option:selected');
            const breakMinutes = selectedOption.data('break-minutes');
            const standardHours = selectedOption.data('standard-hours');
            
            if (breakMinutes !== undefined) {
                lunchBreak.value = breakMinutes;
            }
            if (standardHours !== undefined) {
                standardTime.value = standardHours;
            }
            
            console.log(`[MONTHLY_UPDATE] Calendar 변경: ${selectedOption.text()} -> break: ${breakMinutes}, standard: ${standardHours}`);
        });
        
        // 초기 로드 시에도 값 동기화
        const selectedOption = $(baseCalendar).find('option:selected');
        const breakMinutes = selectedOption.data('break-minutes');
        const standardHours = selectedOption.data('standard-hours');
        
        if (breakMinutes !== undefined) {
            lunchBreak.value = breakMinutes;
        }
        if (standardHours !== undefined) {
            standardTime.value = standardHours;
        }
        // 昼休み区分은 readonly 유지 (기준카레더에 따라 자동 설정되므로)
        ['input', 'change', 'keydown'].forEach(evt => {
            lunchBreak.addEventListener(evt, e => { 
                if (e.type === 'change' && e.target === baseCalendar) return; // calendar 변경은 허용
                e.preventDefault(); 
                e.stopPropagation(); 
                return false; 
            });
        });
        // 기준시간은 사용자가 직접 수정 가능하도록 이벤트 차단하지 않음
    }
}

// 基準カレンダー 변경 시 점심시간/기준시간 자동 세팅
$(document).on('change', '#create-base-calendar', function() {
    const selectedOption = $(this).find('option:selected');
    const breakMinutes = selectedOption.data('break-minutes');
    const standardHours = selectedOption.data('standard-hours');
    
    if (breakMinutes !== undefined) {
        $('#create-lunch-break').val(breakMinutes);
    }
    if (standardHours !== undefined) {
        $('#create-standard-time').val(standardHours);
    }
    
    console.log(`[MONTHLY_CREATE] Calendar 변경: ${selectedOption.text()} -> break: ${breakMinutes}, standard: ${standardHours}`);
});

// 등록 모달 열릴 때 초기값 설정
$(document).on('click', '#create-monthly-btn', function() {
    // Calendar ID 1이 선택된 상태에서 초기값 설정
    const selectedOption = $('#create-base-calendar option:selected');
    const breakMinutes = selectedOption.data('break-minutes');
    const standardHours = selectedOption.data('standard-hours');
    
    if (breakMinutes !== undefined) {
        $('#create-lunch-break').val(breakMinutes);
    }
    if (standardHours !== undefined) {
        $('#create-standard-time').val(standardHours);
    }
    
    console.log(`[MONTHLY_CREATE] 초기값 설정: ${selectedOption.text()} -> break: ${breakMinutes}, standard: ${standardHours}`);
});

// 修正モ달の基準カレンダー 변경 시 점심시간/기준시간 자동 세팅
$(document).on('change', '#update-base-calendar', function() {
    const selectedOption = $(this).find('option:selected');
    const breakMinutes = selectedOption.data('break-minutes');
    const standardHours = selectedOption.data('standard-hours');
    
    if (breakMinutes !== undefined) {
        $('#update-lunch-break').val(breakMinutes);
    }
    if (standardHours !== undefined) {
        $('#update-standard-time').val(standardHours);
    }
});

// ===================== 月情報セクションの表示状態管理 =====================
const MonthlyInfoToggle = {
    getState: function() {
        // 기본값은 항상 닫힘(0)
        const val = localStorage.getItem('monthlyInfoOpen');
        return val === '1';
    },
    setState: function(isOpen) {
        localStorage.setItem('monthlyInfoOpen', isOpen ? '1' : '0');
    },
    updateDisplay: function() {
        // 항상 최신 DOM에서 요소를 다시 탐색
        const section = document.getElementById('monthly-info-section');
        const showBtn = document.getElementById('show-monthly-info-btn');
        const hideBtn = document.getElementById('hide-monthly-info-btn');
        const monthlyDetails = document.querySelector('.monthly-details-grid');
        const registerBtn = document.getElementById('create-monthly-btn');
        const isOpen = this.getState();
        if (monthlyDetails) {
            // 月情報がある場合
            if (section) section.style.display = isOpen ? 'block' : 'none';
            if (showBtn) showBtn.style.display = isOpen ? 'none' : 'inline-block';
            if (hideBtn) hideBtn.style.display = isOpen ? 'inline-block' : 'none';
            if (registerBtn) registerBtn.style.display = 'none';
        } else {
            // 月情報がない場合
            if (section) section.style.display = 'none';
            if (showBtn) showBtn.style.display = 'none';
            if (hideBtn) hideBtn.style.display = 'none';
            if (registerBtn) registerBtn.style.display = 'inline-block';
        }
    },
    bindEvents: function() {
        // 항상 최신 DOM에서 버튼을 다시 탐색하고 이벤트 바인딩
        const showBtn = document.getElementById('show-monthly-info-btn');
        const hideBtn = document.getElementById('hide-monthly-info-btn');
        if (showBtn) {
            showBtn.onclick = () => {
                this.setState(true);
                this.updateDisplay();
            };
        }
        if (hideBtn) {
            hideBtn.onclick = () => {
                this.setState(false);
                this.updateDisplay();
            };
        }
    },
    init: function() {
        this.updateDisplay();
        this.bindEvents();
    }
};
// 최초 진입, ajax 렌더링 후 모두 MonthlyInfoToggle.init() 호출 필요
// 캘린더/월 이동 후 렌더링 시 반드시 아래 함수 2개를 호출해야 함
// updateMonthlyInfoSectionDisplay();
// bindMonthlyInfoToggleEvents();

// ===================== アプリパスワード収得方法ヘルプ =====================
const appPasswordHelpIcon = document.getElementById('app-password-help-icon');
const appPasswordTooltip = document.getElementById('app-password-tooltip');
if (appPasswordHelpIcon && appPasswordTooltip) {
    // ヘルプアイコンをクリックでツールチップを必ず表示（トグルしない）
    appPasswordHelpIcon.addEventListener('click', function(e) {
        e.stopPropagation();
        // 位置調整（?アイコンの右隣・同じ高さに表示）
        appPasswordTooltip.style.top = appPasswordHelpIcon.offsetTop + 'px';
        appPasswordTooltip.style.left = (appPasswordHelpIcon.offsetLeft + appPasswordHelpIcon.offsetWidth + 8) + 'px';
        appPasswordTooltip.style.display = 'block';
    });
    // フォーカスでも開く
    appPasswordHelpIcon.addEventListener('focus', function(e) {
        appPasswordTooltip.style.display = 'block';
    });
    // Xボタンで閉じる
    const tooltipCloseBtn = document.getElementById('app-password-tooltip-close');
    if (tooltipCloseBtn) {
        tooltipCloseBtn.addEventListener('click', function(e) {
            appPasswordTooltip.style.display = 'none';
        });
    }
    // 外部クリックでツールチップを閉じる
    document.addEventListener('mousedown', function(e) {
        if (appPasswordTooltip.style.display === 'block') {
            if (!appPasswordTooltip.contains(e.target) && !appPasswordHelpIcon.contains(e.target)) {
                appPasswordTooltip.style.display = 'none';
            }
        }
    });
    // Escキーで閉じる
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            appPasswordTooltip.style.display = 'none';
        }
    });
    // ツールチップ内リンクは新しいタブで開く（aタグに target=_blank あり)
}

// ===================== 勤務区分ヘルプ =====================
const worktypeHelpIcon = document.getElementById('worktype-help-icon');
const worktypeTooltip = document.getElementById('worktype-tooltip');

// ===================== 残業時間ヘルプ =====================
function setupOvertimeTooltip() {
    console.log('[OVERTIME] 툴팁 이벤트 위임 설정 시작');
    
    // 이벤트 위임을 사용해서 동적으로 생성되는 요소에도 대응
    document.addEventListener('click', function(e) {
        // 잔업 시간 도움말 아이콘 클릭
        if (e.target.closest('#overtime-help-icon')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[OVERTIME] 클릭 이벤트 발생');
            
            const modal = document.getElementById('overtime-tooltip-modal');
            if (modal) {
                modal.style.display = 'flex';
                console.log('[OVERTIME] 모달 표시');
            } else {
                console.warn('[OVERTIME] 모달 요소를 찾을 수 없습니다');
            }
        }
        
        // 닫기 버튼 클릭
        if (e.target.closest('#overtime-tooltip-close')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[OVERTIME] 닫기 버튼 클릭');
            
            const modal = document.getElementById('overtime-tooltip-modal');
            if (modal) {
                modal.style.display = 'none';
                console.log('[OVERTIME] 모달 숨김');
            }
        }
        
        // 오버레이 클릭
        if (e.target.closest('#overtime-modal-overlay')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[OVERTIME] 오버레이 클릭');
            
            const modal = document.getElementById('overtime-tooltip-modal');
            if (modal) {
                modal.style.display = 'none';
                console.log('[OVERTIME] 모달 숨김');
            }
        }
    });
    
    // 포커스 이벤트도 이벤트 위임으로 처리
    document.addEventListener('focus', function(e) {
        if (e.target.closest('#overtime-help-icon')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[OVERTIME] 포커스 이벤트 발생');
            
            const modal = document.getElementById('overtime-tooltip-modal');
            if (modal) {
                modal.style.display = 'flex';
                console.log('[OVERTIME] 모달 표시');
            }
        }
    }, true);
    
    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('overtime-tooltip-modal');
            if (modal && modal.style.display === 'flex') {
                console.log('[OVERTIME] ESC 키 눌림');
                modal.style.display = 'none';
            }
        }
    });
    
    console.log('[OVERTIME] 툴팁 이벤트 위임 설정 완료');
}

// 근무 구분 툴팁 이벤트 위임 설정
function setupWorkTypeTooltip() {
    console.log('[WORKTYPE] 툴팁 이벤트 위임 설정 시작');
    
    // 이벤트 위임을 사용해서 동적으로 생성되는 요소에도 대응
    document.addEventListener('click', function(e) {
        // 근무 구분 도움말 아이콘 클릭
        if (e.target.closest('#worktype-help-icon')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[WORKTYPE] 클릭 이벤트 발생');
            
            const modal = document.getElementById('worktype-tooltip');
            if (modal) {
                modal.style.display = 'flex';
                console.log('[WORKTYPE] 모달 표시');
            } else {
                console.warn('[WORKTYPE] 모달 요소를 찾을 수 없습니다');
            }
        }
        
        // 닫기 버튼 클릭
        if (e.target.closest('#worktype-tooltip-close')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[WORKTYPE] 닫기 버튼 클릭');
            
            const modal = document.getElementById('worktype-tooltip');
            if (modal) {
                modal.style.display = 'none';
                console.log('[WORKTYPE] 모달 숨김');
            }
        }
        
        // 모달 밖 클릭으로 닫기
        const modal = document.getElementById('worktype-tooltip');
        if (modal && modal.style.display === 'flex') {
            // 모달이 열려있고, 모달 밖을 클릭했을 때
            if (!e.target.closest('#worktype-tooltip')) {
                e.preventDefault();
                e.stopPropagation();
                console.log('[WORKTYPE] 모달 밖 클릭');
                modal.style.display = 'none';
                console.log('[WORKTYPE] 모달 숨김');
            }
            // 모달 배경(오버레이) 클릭했을 때
            else if (e.target.closest('#worktype-tooltip') && !e.target.closest('.modal-content')) {
                e.preventDefault();
                e.stopPropagation();
                console.log('[WORKTYPE] 모달 배경 클릭');
                modal.style.display = 'none';
                console.log('[WORKTYPE] 모달 숨김');
            }
        }
    });
    
    // 포커스 이벤트도 이벤트 위임으로 처리
    document.addEventListener('focus', function(e) {
        if (e.target.closest('#worktype-help-icon')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[WORKTYPE] 포커스 이벤트 발생');
            
            const modal = document.getElementById('worktype-tooltip');
            if (modal) {
                modal.style.display = 'flex';
                console.log('[WORKTYPE] 모달 표시');
            }
        }
    }, true);
    
    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('worktype-tooltip');
            if (modal && modal.style.display === 'flex') {
                console.log('[WORKTYPE] ESC 키 눌림');
                modal.style.display = 'none';
            }
        }
    });
    
    console.log('[WORKTYPE] 툴팁 이벤트 위임 설정 완료');
}

// ===================== 勤務区分・休日ユーティリティ =====================
// 指定勤務区分が休日/休暇/欠勤等か判定
function isDayOff(workType) {
    return workType === '年休' || workType === '年休(半)' || workType === '代休' || workType === '振替(休)' || workType === '振替(勤)' || workType === '欠勤' || workType === '特別休暇';
}

// 日付(YYYY-MM-DD)から休日種別('休日','休日(法)','祝日')を取得
function getHolidayTypeByDate(dateStr) {
    console.log(`[HOLIDAY TYPE] 日付: ${dateStr}`);
    
    let holidaysDb = {};
    try {
        holidaysDb = JSON.parse(document.getElementById('holidays-db-data')?.textContent || '{}');
    } catch (e) {
        console.warn('[HOLIDAY TYPE] holidays-db-data 파싱 에러:', e);
    }
    
    let apiHolidays = {};
    try {
        apiHolidays = window.apiHolidays || {};
    } catch (e) {
        console.warn('[HOLIDAY TYPE] window.apiHolidays 접근 에러:', e);
    }
    
    console.log(`[HOLIDAY TYPE] API 공휴일 데이터:`, apiHolidays);
    console.log(`[HOLIDAY TYPE] DB 공휴일 데이터:`, holidaysDb);
    
    if (apiHolidays[dateStr]) {
        console.log(`[HOLIDAY TYPE] API 공휴일 발견: ${dateStr} -> 祝日`);
        return '祝日';
    }
    if (holidaysDb[dateStr]) {
        console.log(`[HOLIDAY TYPE] DB 공휴일 발견: ${dateStr} -> 祝日`);
        return '祝日';
    }
    
    const d = new Date(dateStr);
    if (isNaN(d)) {
        console.warn(`[HOLIDAY TYPE] 날짜 파싱 실패: ${dateStr}`);
        return null;
    }
    
    if (d.getDay() === 0) {
        console.log(`[HOLIDAY TYPE] 일요일: 休日(法)`);
        return '休日(法)'; // 日曜
    }
    if (d.getDay() === 6) {
        console.log(`[HOLIDAY TYPE] 토요일: 休日`);
        return '休日';     // 土曜
    }
    
    console.log(`[HOLIDAY TYPE] 평일: null`);
    return null;
}

// 勤務区分セレクトオプションを日付基準でフィルタリング
function filterWorkTypeOptionsByDate(dateStr) {
    const workTypeSelect = document.querySelector('select[name="work_type"]');
    if (!workTypeSelect) return;
    const holidayType = getHolidayTypeByDate(dateStr);
    if (holidayType) {
        Array.from(workTypeSelect.options).forEach(option => {
            const value = option.value;
            const shouldShow = value === holidayType || value === '振替(勤)' || value === '';
            option.style.display = shouldShow ? '' : 'none';
        });
    } else {
        Array.from(workTypeSelect.options).forEach(option => {
            const value = option.value;
            const isRestrictedHolidayType = value === '休日(法)' || value === '祝日' || value === '振替(勤)';
            const isDaiQ = value === value === '振替(勤)';
            const shouldShow = !isRestrictedHolidayType && !isDaiQ && value !== '';
            option.style.display = shouldShow ? '' : 'none';
        });
    }
}

// 勤務区分に応じてフォーム状態를同기 (toggleAltWorkDateField와 같은 방식)
function syncFormStateByWorkType(workType, startTimeInput, endTimeInput, normalHoursBtn) {
    console.log(`[SYNC] syncFormStateByWorkType 호출 시작`);
    console.log(`[SYNC] 파라미터:`, {
        workType: workType,
        startTimeInput: startTimeInput,
        endTimeInput: endTimeInput,
        normalHoursBtn: normalHoursBtn
    });
    
    if (!startTimeInput || !endTimeInput || !normalHoursBtn) {
        console.log(`[SYNC] 파라미터 누락으로 함수 종료`);
        return;
    }
    
    console.log(`[SYNC] syncFormStateByWorkType 실행: workType=${workType}`);
    
    // 월정보 존재 여부 확인 (monthly-details-grid 요소로 판단)
    const monthlyDetails = document.querySelector('.monthly-details-grid');
    const hasMonthlyData = monthlyDetails !== null;
    
    console.log(`[SYNC] 월정보 존재: ${hasMonthlyData}`);
    
    // 휴가 타입인지 확인 (toggleAltWorkDateField처럼 직접 체크)
    const isHolidayType = workType === '年休' || workType === '年休(半)' || workType === '代休' || workType === '振替(休)' || workType === '振替(勤)' || workType === '欠勤' || workType === '特別休暇' ;
    
    console.log(`[SYNC] 휴가 타입 여부: ${isHolidayType}`);
    
    if (isHolidayType) {
        // 휴가 타입: 시간 입력 필드만 비활성화 (通常 버튼은 활성화 유지)
        startTimeInput.value = '00:00';
        endTimeInput.value = '00:00';
        startTimeInput.readOnly = true;
        endTimeInput.readOnly = true;
        // normalHoursBtn.disabled = true;  // 주석처리
        console.log(`[SYNC] 휴가 타입 → 시간 입력 필드만 비활성화, 通常 버튼은 활성화 유지`);
    } else {
        // 근무 타입: 시간 입력 필드와 通常 버튼 상태 설정
        startTimeInput.readOnly = false;
        endTimeInput.readOnly = false;
        // 통상 버튼은 항상 활성화
        // normalHoursBtn.disabled = !hasMonthlyData;  // 주석처리
        console.log(`[SYNC] 근무 타입 → 통상 버튼 항상 활성화`);
    }
}

// 代休/振替の勤務日フィール드表示制御
function toggleAltWorkDateField(workType) {
    console.log(`[TOGGLE] toggleAltWorkDateField 호출: workType=${workType}`);
    
    const altGroup = document.getElementById('alt-work-date-group');
    const altInput = altGroup?.querySelector('input[type="date"]');
    const requiredMark = document.getElementById('alt-work-date-required');
    
    console.log(`[TOGGLE] 요소 찾기 결과:`, {
        altGroup: altGroup,
        altInput: altInput,
        requiredMark: requiredMark
    });
    
    if (!altGroup || !altInput) {
        console.warn('[TOGGLE] alt-work-date-group 또는 input 요소를 찾을 수 없습니다');
        return;
    }
    
    const showTypes = ['振替(勤)', '振替(休)', '休日', '休日(法)', '祝日', '代休'];
    const requiredTypes = ['振替(勤)', '振替(休)', '代休']; // 필수 입력이 필요한 근무구분들
    
    console.log(`[TOGGLE] showTypes:`, showTypes);
    console.log(`[TOGGLE] requiredTypes:`, requiredTypes);
    console.log(`[TOGGLE] workType이 showTypes에 포함되는가:`, showTypes.includes(workType));
    
    if (showTypes.includes(workType)) {
        // 표시
        altGroup.style.display = '';
        
        // 필수 입력 여부 설정
        if (requiredTypes.includes(workType)) {
            altInput.required = true;
            if (requiredMark) requiredMark.style.display = 'inline';
            console.log(`[TOGGLE] 대체근무일 필드 표시 (필수): ${workType}`);
        } else {
            altInput.required = false;
            if (requiredMark) requiredMark.style.display = 'none';
            console.log(`[TOGGLE] 대체근무일 필드 표시 (선택): ${workType}`);
        }
    } else {
        // 숨김
        altGroup.style.display = 'none';
        altInput.required = false;
        if (requiredMark) requiredMark.style.display = 'none';
        console.log(`[TOGGLE] 대체근무일 필드 숨김: ${workType}`);
    }
}

// フォーム警告メッセージ表示
function showFormWarning(msg) {
    const warningEl = document.querySelector('.disabled-message');
    if (warningEl) {
        warningEl.style.display = 'block';
        const msgEl = warningEl.querySelector('p');
        if (msgEl) {
            msgEl.innerHTML = `<i class="fa-solid fa-info-circle"></i> ${msg}`;
        }
        console.log('[FORM] 警告メッセージ表示:', msg);
    }
}

// フォーム警告メッセージ非表示
function hideFormWarning() {
    const warningEl = document.querySelector('.disabled-message');
    if (warningEl) {
        warningEl.style.display = 'none';
        console.log('[FORM] 警告メッセージ非表示');
    }
}

// アンケートを開く関数
function openSurvey() {
    console.log('[DEBUG] openSurvey 함수 호출됨');
    const surveyUrl = 'https://docs.google.com/forms/d/e/1FAIpQLSdRmdDHYjOKITFvv3_FXRq-9FPTm-mNGTSsuNNNKX4KDvENCg/viewform?usp=dialog';
    console.log('[DEBUG] 설문조사 URL:', surveyUrl);
    const newWindow = window.open(surveyUrl, '_blank', 'width=800,height=600,scrollbars=yes,resizable=yes');
    console.log('[DEBUG] 새 창 열기 결과:', newWindow);
    console.log('[SURVEY] アンケートを開きました');
}

// 전역 스코프에 노출 (HTML onclick에서도 사용 가능하도록)
window.openSurvey = openSurvey;

// 설문조사 버튼 이벤트 바인딩 함수
function bindSurveyButtonEvents() {
    console.log('[DEBUG] 설문조사 버튼 이벤트 바인딩 시작');
    const surveyBtn = document.getElementById('survey-btn');
    console.log('[DEBUG] 설문조사 버튼 찾기:', surveyBtn);
    
    if (surveyBtn) {
        // 기존 이벤트 리스너 제거 (중복 방지)
        surveyBtn.removeEventListener('click', openSurvey);
        // 새 이벤트 리스너 추가
        surveyBtn.addEventListener('click', (e) => {
            console.log('[DEBUG] 설문조사 버튼 클릭됨');
            openSurvey();
        });
        console.log('[DEBUG] 설문조사 버튼 이벤트 리스너 등록 완료');
    } else {
        console.warn('[DEBUG] 설문조사 버튼을 찾을 수 없습니다');
    }
}

// ===================== AJAX 섹션 업데이트 함수 =====================

// ===================== 초기화 및 상태 복원 =====================

/**
 * 페이지 로드 시 초기 상태 복원
 */
function restoreInitialState() {
    // 서버에서 이미 토글 상태에 따라 올바르게 렌더링되었으므로
    // 추가적인 클라이언트 측 처리는 불필요
    console.log('[INIT] 서버에서 토글 상태 처리됨');
    
    // 日替りチェックボックスの初期状態を確認
    setTimeout(() => {
        checkDayChange();
    }, 100);
}

// 勤務区分のツールチップ設定関数
function setupWorkTypeTooltip() {
    const worktypeHelpIcon = document.getElementById('worktype-help-icon');
    const worktypeTooltip = document.getElementById('worktype-tooltip');
    
    if (!worktypeHelpIcon || !worktypeTooltip) {
        console.warn('[TOOLTIP] ツールチップ要素が見つかりません');
        return;
    }
    
    // 既存のイベントリスナーを削除 (重複防止)
    worktypeHelpIcon.removeEventListener('click', handleWorktypeTooltipClick);
    worktypeHelpIcon.removeEventListener('focus', handleWorktypeTooltipFocus);
    
    // 新しいイベントリスナーを追加
    worktypeHelpIcon.addEventListener('click', handleWorktypeTooltipClick);
    worktypeHelpIcon.addEventListener('focus', handleWorktypeTooltipFocus);
    
    // 閉じるボタンイベント
    const worktypeTooltipCloseBtn = document.getElementById('worktype-tooltip-close');
    if (worktypeTooltipCloseBtn) {
        worktypeTooltipCloseBtn.removeEventListener('click', handleWorktypeTooltipClose);
        worktypeTooltipCloseBtn.addEventListener('click', handleWorktypeTooltipClose);
    }
}

// 툴팁 위치 계산 함수 (화면 경계 체크만)
function positionTooltip(triggerElement, tooltipElement) {
    const triggerRect = triggerElement.getBoundingClientRect();
    const tooltipRect = tooltipElement.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    
    // CSS로 기본 위치는 설정되어 있음 (top: 50%, left: 100%)
    // 화면 오른쪽을 벗어나는 경우만 왼쪽으로 이동
    if (triggerRect.right + tooltipRect.width + 8 > viewportWidth) {
        tooltipElement.style.left = 'auto';
        tooltipElement.style.right = '100%';
        tooltipElement.style.marginLeft = '0';
        tooltipElement.style.marginRight = '8px';
    } else {
        // 기본 위치로 리셋
        tooltipElement.style.left = '100%';
        tooltipElement.style.right = 'auto';
        tooltipElement.style.marginLeft = '8px';
        tooltipElement.style.marginRight = '0';
    }
}

// ツールチップイベントハンドラ
function handleWorktypeTooltipClick(e) {
    e.stopPropagation();
    const worktypeTooltip = document.getElementById('worktype-tooltip');
    const worktypeHelpIcon = document.getElementById('worktype-help-icon');
    
    if (worktypeTooltip && worktypeHelpIcon) {
        // 툴팁 위치를 동적으로 계산
        positionTooltip(worktypeHelpIcon, worktypeTooltip);
        worktypeTooltip.style.display = 'block';
    }
}

function handleWorktypeTooltipFocus(e) {
    const worktypeTooltip = document.getElementById('worktype-tooltip');
    const worktypeHelpIcon = document.getElementById('worktype-help-icon');
    
    if (worktypeTooltip && worktypeHelpIcon) {
        // 툴팁 위치를 동적으로 계산
        positionTooltip(worktypeHelpIcon, worktypeTooltip);
        worktypeTooltip.style.display = 'block';
    }
}

function handleWorktypeTooltipClose(e) {
    const worktypeTooltip = document.getElementById('worktype-tooltip');
    if (worktypeTooltip) {
        worktypeTooltip.style.display = 'none';
    }
}

// ===================== 日替りチェックボックス管理関数 =====================

/**
 * 開始時刻と終了時刻を比較して、日替りチェックボックスを自動チェックする関数
 * end_timeがstart_timeより前の時刻の場合、自動的にチェックされる
 */
function checkDayChange() {
    const startTimeInput = document.querySelector('input[name="start_time"]');
    const endTimeInput = document.querySelector('input[name="end_time"]');
    const dayChangeCheckbox = document.getElementById('day_change_checkbox');
    
    if (!startTimeInput || !endTimeInput || !dayChangeCheckbox) {
        console.warn('[DAY_CHANGE] 必要な要素が見つかりません');
        return;
    }
    
    const startTime = startTimeInput.value;
    const endTime = endTimeInput.value;
    
    if (!startTime || !endTime) {
        return; // 時刻が入力されていない場合は何もしない
    }
    
    // 時刻を比較して日替りかどうかを判定
    const isDayChange = endTime < startTime;
    
    // チェックボックスを自動チェック/アンチェック
    dayChangeCheckbox.checked = isDayChange;
    
    console.log(`[DAY_CHANGE] 開始時刻: ${startTime}, 終了時刻: ${endTime}, 日替り: ${isDayChange}`);
}

// 在宅ボタンクリック時の処理
function addZaitakuToNotes() {
    const notesTextarea = document.getElementById('id_notes');
    if (!notesTextarea) {
        console.error('[ZAITAKU] 備考テキストエリアが見つかりません');
        return;
    }
    
    const currentValue = notesTextarea.value;
    const zaitakuText = ' 在宅';
    
    // 既に「在宅」が含まれているかチェック
    if (currentValue.includes('在宅')) {
        console.log('[ZAITAKU] 既に「在宅」が含まれています');
        return;
    }
    
    // 現在の値の末尾に「 在宅」を追加
    const newValue = currentValue + zaitakuText;
    notesTextarea.value = newValue;
    
    // テキストエリアにフォーカスを当ててカーソルを末尾に移動
    notesTextarea.focus();
    notesTextarea.setSelectionRange(newValue.length, newValue.length);
    
    console.log('[ZAITAKU] 備考に「在宅」を追加しました');
}

// DOM読み込み完了時に初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeState();
        restoreInitialState();
    });
} else {
    initializeState();
    restoreInitialState();
}