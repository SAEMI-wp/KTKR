// 직원 상세 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 읽기 전용 모드 설정
    const READ_ONLY_MODE = true;
    const CURRENT_EMPLOYEE_ID = document.querySelector('#current-month-display')?.dataset?.employeeId || '';
    const CURRENT_YEAR = parseInt(document.querySelector('#current-month-display')?.dataset?.year || '2025');
    const CURRENT_MONTH = parseInt(document.querySelector('#current-month-display')?.dataset?.month || '8');

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

    // 프린트 버튼 기능 (버튼이 존재할 때만)
    const printPreviewBtn = document.getElementById('print-preview-btn');
    if (printPreviewBtn) {
        printPreviewBtn.addEventListener('click', function() {
            const printModal = document.getElementById('print-modal');
            if (printModal) {
                printModal.style.display = 'block';
            }
        });
    }

    // 모달 닫기
    const modals = document.querySelectorAll('.modal');
    const closeBtns = document.querySelectorAll('.close');
    
    closeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            modals.forEach(modal => modal.style.display = 'none');
        });
    });

    window.addEventListener('click', function(event) {
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });

    // 프린트 옵션 버튼들 (버튼들이 존재할 때만)
    const pdfPreviewBtn = document.getElementById('pdf-preview-btn');
    const pdfDownloadBtn = document.getElementById('pdf-download-btn');
    const excelDownloadBtn = document.getElementById('excel-download-btn');

    if (pdfPreviewBtn) {
        pdfPreviewBtn.addEventListener('click', function() {
            window.open(`/attendance/pdf/preview/?employee_id=${CURRENT_EMPLOYEE_ID}&year=${CURRENT_YEAR}&month=${CURRENT_MONTH}`, '_blank');
        });
    }

    if (pdfDownloadBtn) {
        pdfDownloadBtn.addEventListener('click', function() {
            window.location.href = `/attendance/pdf/preview/?employee_id=${CURRENT_EMPLOYEE_ID}&year=${CURRENT_YEAR}&month=${CURRENT_MONTH}&download=1`;
        });
    }

    if (excelDownloadBtn) {
        excelDownloadBtn.addEventListener('click', function() {
            window.location.href = `/attendance/excel/download/?employee_id=${CURRENT_EMPLOYEE_ID}&year=${CURRENT_YEAR}&month=${CURRENT_MONTH}`;
        });
    }
}); 