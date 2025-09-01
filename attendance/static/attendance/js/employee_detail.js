// 직원 상세 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 읽기 전용 모드 설정
    const READ_ONLY_MODE = true;
    const CURRENT_EMPLOYEE_ID = document.querySelector('#current-month-display')?.dataset?.employeeId || '';
    const CURRENT_YEAR = parseInt(document.querySelector('#current-month-display')?.dataset?.year || '2025');
    const CURRENT_MONTH = parseInt(document.querySelector('#current-month-display')?.dataset?.month || '8');
    
    // 월별 데이터 캐시 (성능 향상을 위해) - 전역으로 설정
    window.monthDataCache = new Map();

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