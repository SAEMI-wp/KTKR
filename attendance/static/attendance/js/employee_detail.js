// 직원 상세 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 읽기 전용 모드 설정
    const READ_ONLY_MODE = true;
    const CURRENT_EMPLOYEE_ID = document.querySelector('#current-month-display')?.dataset?.employeeId || '';
    const CURRENT_YEAR = parseInt(document.querySelector('#current-month-display')?.dataset?.year || '2025');
    const CURRENT_MONTH = parseInt(document.querySelector('#current-month-display')?.dataset?.month || '8');
    
    // 월별 데이터 캐시 (성능 향상을 위해) - 전역으로 설정
    window.monthDataCache = new Map();

    // 공휴일 표시 초기화
    applyAllHolidaysToCalendar();

    // 월 이동 기능
    window.navigateMonth = function(direction) {
        let newYear = CURRENT_YEAR;
        let newMonth = CURRENT_MONTH;
        
        if (direction === 'prev') {
            if (newMonth === 1) {
                newMonth = 12;
                newYear--;
            } else {
                newMonth--;
            }
        } else {
            if (newMonth === 12) {
                newMonth = 1;
                newYear++;
            } else {
                newMonth++;
            }
        }
        
        window.location.href = `/admin/employee/${CURRENT_EMPLOYEE_ID}/detail/${newYear}/${newMonth.toString().padStart(2, '0')}/`;
    };

    // 탭 전환 기능 (탭이 존재할 때만)
    const tabCalendar = document.getElementById('tab-calendar');
    const tabList = document.getElementById('tab-list');
    const calendarTab = document.getElementById('calendar-tab');
    const listTab = document.getElementById('list-tab');

    if (tabCalendar && tabList && calendarTab && listTab) {
        tabCalendar.addEventListener('click', function() {
            tabCalendar.classList.add('active');
            tabList.classList.remove('active');
            calendarTab.style.display = 'block';
            listTab.style.display = 'none';
        });

        tabList.addEventListener('click', function() {
            tabList.classList.add('active');
            tabCalendar.classList.remove('active');
            listTab.style.display = 'block';
            calendarTab.style.display = 'none';
        });
    }

    // ===================== 월/년 표시 클릭 이벤트 =====================
    const monthDisplay = document.getElementById('current-month-display');
    if (monthDisplay) {
        monthDisplay.style.cursor = 'pointer';
        monthDisplay.addEventListener('click', handleMonthDisplayClick);
    }

    // ===================== 인쇄 버튼 이벤트 =====================
    const printPreviewBtn = document.getElementById('print-preview-btn');
    if (printPreviewBtn) {
        printPreviewBtn.addEventListener('click', function() {
            // 바로 PDF 미리보기 모달 열기
            const pdfUrl = `/attendance/pdf/preview/?year=${CURRENT_YEAR}&month=${CURRENT_MONTH.toString().padStart(2, '0')}&employee_no=${CURRENT_EMPLOYEE_ID}`;
            const pdfIframe = document.getElementById('pdf-iframe');
            const pdfModal = document.getElementById('pdf-preview-modal');
            
            if (pdfIframe && pdfModal) {
                pdfIframe.src = pdfUrl;
                pdfModal.classList.add('show');
            }
        });
    }

    // ===================== 모달 닫기 이벤트 =====================
    // 월/년 선택 모달 닫기
    const closePickerBtn = document.getElementById('close-picker-btn');
    if (closePickerBtn) {
        closePickerBtn.addEventListener('click', function() {
            const pickerModal = document.getElementById('year-month-picker-modal');
            if (pickerModal) pickerModal.classList.remove('show');
        });
    }

    // PDF 미리보기 모달 닫기
    const closePdfModalBtn = document.getElementById('close-pdf-modal-btn');
    if (closePdfModalBtn) {
        closePdfModalBtn.addEventListener('click', function() {
            const pdfModal = document.getElementById('pdf-preview-modal');
            if (pdfModal) pdfModal.classList.remove('show');
            const pdfIframe = document.getElementById('pdf-iframe');
            if (pdfIframe) pdfIframe.src = '';
        });
    }

    // 모달 외부 클릭 시 닫기
    const modals = document.querySelectorAll('.modal-overlay');
    modals.forEach(modal => {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.classList.remove('show');
            }
        });
    });

    // ===================== PDF 미리보기 모달 내부 버튼 이벤트 =====================
    const printPdfBtn = document.getElementById('print-pdf-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const downloadExcelBtn = document.getElementById('download-excel-btn');

    if (printPdfBtn) {
        printPdfBtn.addEventListener('click', function() {
            const iframe = document.getElementById('pdf-iframe');
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.print();
            }
        });
    }

    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', function() {
            window.location.href = `/attendance/pdf/download/?year=${CURRENT_YEAR}&month=${CURRENT_MONTH.toString().padStart(2, '0')}&employee_no=${CURRENT_EMPLOYEE_ID}`;
        });
    }

    if (downloadExcelBtn) {
        downloadExcelBtn.addEventListener('click', function() {
            window.location.href = `/attendance/excel/download/?year=${CURRENT_YEAR}&month=${CURRENT_MONTH.toString().padStart(2, '0')}&employee_no=${CURRENT_EMPLOYEE_ID}`;
        });
    }
});

// ===================== 월/년 표시 클릭 핸들러 =====================
async function handleMonthDisplayClick() {
    const monthDisplay = document.getElementById('current-month-display');
    const pickerModal = document.getElementById('year-month-picker-modal');
    if (!monthDisplay || !pickerModal) return;
    
    let currentYear = parseInt(monthDisplay.dataset.year) || new Date().getFullYear();
    await updateYearMonthPicker(currentYear);
    pickerModal.classList.add('show');

    // 월 버튼 이벤트 바인딩
    const monthGrid = document.querySelector('.month-grid');
    if (monthGrid) {
        const newMonthGrid = monthGrid.cloneNode(true);
        monthGrid.parentNode.replaceChild(newMonthGrid, monthGrid);
        newMonthGrid.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                // no-data 클래스가 있으면 클릭 방지
                if (e.target.classList.contains('no-data')) {
                    return;
                }
                const selectedMonth = e.target.dataset.month;
                const employeeId = monthDisplay.dataset.employeeId;
                window.location.href = `/admin/employee/${employeeId}/detail/${currentYear}/${selectedMonth.padStart(2, '0')}/`;
            }
        });
    }

    // 년도 이동 버튼 이벤트 바인딩
    const pickerYearDisplay = document.getElementById('picker-year');
    const prevYearBtn = document.getElementById('prev-year-btn');
    const nextYearBtn = document.getElementById('next-year-btn');
    
    if (prevYearBtn && nextYearBtn && pickerYearDisplay) {
        prevYearBtn.replaceWith(prevYearBtn.cloneNode(true));
        nextYearBtn.replaceWith(nextYearBtn.cloneNode(true));
        const newPrevYearBtn = document.getElementById('prev-year-btn');
        const newNextYearBtn = document.getElementById('next-year-btn');
        
        newPrevYearBtn.addEventListener('click', async () => {
            currentYear--;
            await updateYearMonthPicker(currentYear);
            pickerYearDisplay.textContent = currentYear;
        });
        
        newNextYearBtn.addEventListener('click', async () => {
            currentYear++;
            await updateYearMonthPicker(currentYear);
            pickerYearDisplay.textContent = currentYear;
        });
    }
}

// ===================== 월/년 선택기 업데이트 =====================
async function updateYearMonthPicker(year) {
    const monthGrid = document.querySelector('.month-grid');
    const pickerYearDisplay = document.getElementById('picker-year');
    const employeeId = document.querySelector('#current-month-display')?.dataset?.employeeId;
    
    if (monthGrid) {
        // 년도 표시 업데이트 (즉시)
        if (pickerYearDisplay) {
            pickerYearDisplay.textContent = year;
        }
        
        // 기존 버튼들이 있는지 확인
        const existingButtons = monthGrid.querySelectorAll('.month-button');
        const hasExistingButtons = existingButtons.length > 0;
        
        // 기존 버튼이 있으면 로딩 표시만
        if (hasExistingButtons) {
            monthGrid.style.opacity = '0.6';
        } else {
            // 첫 로딩이면 버튼들을 먼저 생성
            monthGrid.innerHTML = '';
            for (let month = 1; month <= 12; month++) {
                const button = document.createElement('button');
                button.textContent = `${month}月`;
                button.dataset.month = month.toString().padStart(2, '0');
                button.className = 'month-button';
                monthGrid.appendChild(button);
            }
        }
        
        // 모든 월에 대해 데이터 존재 여부 확인 (캐시 활용)
        const monthDataPromises = [];
        for (let month = 1; month <= 12; month++) {
            monthDataPromises.push(checkMonthData(employeeId, year, month));
        }
        
        try {
            const monthDataResults = await Promise.all(monthDataPromises);
            
            // 버튼들의 스타일만 업데이트
            const buttons = monthGrid.querySelectorAll('.month-button');
            for (let month = 1; month <= 12; month++) {
                const button = buttons[month - 1];
                if (button) {
                    // no-data 클래스 제거 후 필요시 다시 추가
                    button.classList.remove('no-data');
                    if (!monthDataResults[month - 1]) {
                        button.classList.add('no-data');
                    }
                }
            }
        } catch (error) {
            console.error('월별 데이터 확인 중 오류:', error);
            // 오류 발생 시 모든 버튼을 활성화
            const buttons = monthGrid.querySelectorAll('.month-button');
            buttons.forEach(button => button.classList.remove('no-data'));
        }
        
        // 로딩 완료 후 원래 투명도로 복원
        monthGrid.style.opacity = '1';
    }
}

// ===================== 월별 데이터 확인 함수 =====================
async function checkMonthData(employeeId, year, month) {
    // 전역 캐시 변수에 접근
    const cacheKey = `${employeeId}-${year}-${month}`;
    
    // 캐시에 데이터가 있으면 반환
    if (window.monthDataCache && window.monthDataCache.has(cacheKey)) {
        return window.monthDataCache.get(cacheKey);
    }
    
    try {
        const response = await fetch(`/admin/employee/${employeeId}/monthly-check/?year=${year}&month=${month.toString().padStart(2, '0')}`);
        if (response.ok) {
            const data = await response.json();
            const hasData = data.has_data;
            
            // 캐시에 저장
            if (window.monthDataCache) {
                window.monthDataCache.set(cacheKey, hasData);
            }
            
            return hasData;
        }
        return false;
    } catch (error) {
        console.error(`월별 데이터 확인 오류 (${year}-${month}):`, error);
        return false;
    }
}

// ===================== 공휴일 처리 함수 =====================

/**
 * 공휴일 정보를 캘린더 셀에 적용
 * @param {HTMLElement} td - 캘린더 셀 요소
 * @param {string} holidayName - 공휴일 명칭
 * @param {string} type - 공휴일 타입 ('api', 'db', 'common', 'base', 'green')
 */
function applyHolidayToCell(td, holidayName, type) {
    // holiday-category 요소 찾기 또는 생성
    let holidayCategory = td.querySelector('.holiday-category');
    
    if (!holidayCategory) {
        const cellHeader = td.querySelector('.cell-header');
        if (!cellHeader) {
            return;
        }
        holidayCategory = document.createElement('span');
        holidayCategory.className = 'holiday-category';
        cellHeader.appendChild(holidayCategory);
    }
    
    // 기존 공휴일 요소 제거 (중복 방지)
    const existingItems = holidayCategory.querySelectorAll('.holiday-cat-item');
    existingItems.forEach(item => {
        if (item.classList.contains(type)) {
            item.remove();
        }
    });
    
    // 새로운 공휴일 요소 생성
    const holidaySpan = document.createElement('span');
    holidaySpan.className = `holiday-cat-item ${type}`;
    holidaySpan.textContent = holidayName;
    holidayCategory.appendChild(holidaySpan);
    
    // 날짜 숫자에 holiday 클래스 추가 (빨간색 표시)
    const dateNumber = td.querySelector('.date-number');
    if (dateNumber && !dateNumber.classList.contains('holiday')) {
        dateNumber.classList.add('holiday');
    }
}

/**
 * 일본 공휴일 API 데이터를 캘린더에 적용
 */
async function applyApiHolidaysToCalendar() {
    const apiHolidays = window.apiHolidays || {};
    const monthDisplay = document.getElementById('current-month-display');
    if (!monthDisplay) return;
    
    const year = parseInt(monthDisplay.dataset.year);
    const month = parseInt(monthDisplay.dataset.month);
    const monthStr = String(month).padStart(2, '0');
    
    let appliedCount = 0;
    
    // 해당 월의 공휴일만 필터링하여 적용
    Object.entries(apiHolidays).forEach(([date, holidayName]) => {
        if (date.startsWith(`${year}-${monthStr}`)) {
            const td = document.querySelector(`.calendar-table td[data-date='${date}']`);
            if (td) {
                applyHolidayToCell(td, holidayName, 'api');
                appliedCount++;
            }
        }
    });
}

/**
 * DB holidays_db에서 공통/개별(calendar_name) 공휴일을 캘린더에 표시
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
    
    const tds = document.querySelectorAll('.calendar-table td[data-date]');
    let appliedCount = 0;
    
    tds.forEach(td => {
        const dateStr = td.getAttribute('data-date');
        
        if (holidaysDb[dateStr]) {
            holidaysDb[dateStr].forEach(holiday => {
                let type = 'db';
                
                if (holiday.calendar_name === '共通') {
                    type = 'common';
                } else if (holiday.category === '年休収得') {
                    type = 'green';
                } else {
                    type = 'base';
                }
                
                applyHolidayToCell(td, holiday.holiday_name, type);
                appliedCount++;
            });
        }
    });
}

/**
 * 기존 공휴일 표시 초기화
 */
function clearAllHolidaysFromCalendar() {
    const tds = document.querySelectorAll('.calendar-table td[data-date]');
    
    tds.forEach(td => {
        // holiday-category 내의 모든 공휴일 요소 제거
        const holidayCategory = td.querySelector('.holiday-category');
        if (holidayCategory) {
            holidayCategory.innerHTML = '';
        }
        
        // date-number의 holiday 클래스 제거
        const dateNumber = td.querySelector('.date-number');
        if (dateNumber) {
            dateNumber.classList.remove('holiday');
        }
    });
}

/**
 * 모든 공휴일 표시 (초기화 포함)
 * API 공휴일과 DB 공휴일을 모두 캘린더에 적용
 */
async function applyAllHolidaysToCalendar() {
    // 1. 기존 공휴일 표시 초기화
    clearAllHolidaysFromCalendar();
    
    // 2. API 공휴일 적용
    await applyApiHolidaysToCalendar();
    
    // 3. DB 공휴일 적용
    applyDbHolidaysToCalendar();
} 