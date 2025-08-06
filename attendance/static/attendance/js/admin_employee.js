// Django Admin Employee List Custom JavaScript
console.log('[DEBUG] admin_employee.js 로드됨');

// 여러 방법으로 DOM 로딩 확인
function initCustomAdmin() {
    console.log('[DEBUG] initCustomAdmin 실행됨');
    
    // 1. H1 제목 삭제
    const h1Elements = document.querySelectorAll('h1');
    console.log('[DEBUG] H1 요소들:', h1Elements);
    h1Elements.forEach(h1 => {
        if (h1.textContent.includes('変更する 従業員 を選択')) {
            h1.style.display = 'none';
            console.log('[DEBUG] H1 숨김 완료');
        }
    });

    // 2. 액션 카운터 메시지 삭제
    const actionCounters = document.querySelectorAll('[data-actions-icnt]');
    console.log('[DEBUG] 액션 카운터들:', actionCounters);
    actionCounters.forEach(counter => {
        counter.style.display = 'none';
        console.log('[DEBUG] 액션 카운터 숨김 완료');
    });

    // 3. "操作:" 라벨 삭제
    const labels = document.querySelectorAll('label');
    console.log('[DEBUG] 라벨들:', labels);
    labels.forEach(label => {
        if (label.textContent.includes('操作')) {
            label.style.display = 'none';
            console.log('[DEBUG] 操作 라벨 숨김 완료');
        }
    });

    // 4. 액션 드롭다운 숨기기
    const selects = document.querySelectorAll('select');
    console.log('[DEBUG] select 요소들:', selects);
    selects.forEach(select => {
        if (select.name === 'action') {
            select.style.display = 'none';
            console.log('[DEBUG] 액션 select 숨김 완료');
        }
    });

    // 5. nav-filter 요소 숨기기
    const navFilter = document.getElementById('nav-filter');
    if (navFilter) {
        navFilter.style.display = 'none';
        console.log('[DEBUG] nav-filter 숨김 완료');
    }

    // 6. 실행 버튼 숨기기 - 더 강력하게
    const submitButtons = document.querySelectorAll('input[type="submit"]');
    console.log('[DEBUG] submit 버튼들:', submitButtons);
    submitButtons.forEach(button => {
        // 모든 submit 버튼을 숨김
        button.style.display = 'none';
        button.style.visibility = 'hidden';
        button.style.opacity = '0';
        button.style.position = 'absolute';
        button.style.left = '-9999px';
        button.style.width = '0';
        button.style.height = '0';
        button.style.margin = '0';
        button.style.padding = '0';
        button.style.border = 'none';
        button.style.overflow = 'hidden';
        button.style.pointerEvents = 'none';
        console.log('[DEBUG] 실행 버튼 숨김 완료:', button);
    });

    // 7. 실행 버튼이 포함된 컨테이너도 숨기기
    const submitRows = document.querySelectorAll('.submit-row');
    submitRows.forEach(row => {
        row.style.display = 'none';
        console.log('[DEBUG] submit-row 숨김 완료');
    });

    // 8. 액션 라인에 커스텀 버튼들 추가
    const actionRows = document.querySelectorAll('.actions');
    console.log('[DEBUG] 액션 행들:', actionRows);
    
    actionRows.forEach(actionRow => {
        if (actionRow) {
            // 현재 URL에서 is_active 필터 확인
            const urlParams = new URLSearchParams(window.location.search);
            const isActiveFilter = urlParams.get('is_active');
            console.log('[DEBUG] is_active 필터:', isActiveFilter);
            
            // 추가로 URL에서 직접 확인
            const currentUrl = window.location.href;
            const isRetiredPage = currentUrl.includes('is_active=0') || 
                                 currentUrl.includes('is_active__exact=0') ||
                                 currentUrl.includes('is_active=0&') ||
                                 currentUrl.includes('&is_active=0');
            console.log('[DEBUG] 현재 URL:', currentUrl);
            console.log('[DEBUG] 퇴사자 페이지 여부:', isRetiredPage);
            
            // 필터 드롭다운에서 직접 확인
            const filterSelects = document.querySelectorAll('select');
            let isRetiredFilter = false;
            filterSelects.forEach(select => {
                if (select.name && select.name.includes('is_active')) {
                    console.log('[DEBUG] 필터 select 발견:', select.name, select.value);
                    if (select.value === '0') {
                        isRetiredFilter = true;
                    }
                }
            });
            
            console.log('[DEBUG] 필터에서 확인한 퇴사자 여부:', isRetiredFilter);
            
            // 기존 커스텀 버튼들 제거 (중복 방지)
            const existingButtons = actionRow.querySelectorAll('#retire-selected-btn, #delete-selected-btn, #restore-selected-btn');
            existingButtons.forEach(btn => btn.remove());
            
            // 버튼 컨테이너 생성
            const buttonContainer = document.createElement('div');
            buttonContainer.style.display = 'inline-block';
            buttonContainer.style.float = 'right';
            buttonContainer.style.marginLeft = '10px';
            
            // 퇴사자 페이지인지 확인 (여러 방법으로)
            const isRetiredEmployeePage = isActiveFilter === '0' || isRetiredPage || isRetiredFilter;
            console.log('[DEBUG] 최종 퇴사자 페이지 여부:', isRetiredEmployeePage);
            
            if (isRetiredEmployeePage) {
                // 퇴사자 목록일 때: 복원, 영구삭제 버튼
                buttonContainer.innerHTML = `
                    <button type="button" id="restore-selected-btn" class="custom-action-button">
                        復元
                    </button>
                    <button type="button" id="delete-selected-btn" class="custom-action-button">
                        永久削除
                    </button>
                `;
                console.log('[DEBUG] 퇴사자 버튼 생성: 復元, 永久削除');
            } else {
                // 활성 직원 목록일 때: 퇴사 처리 버튼
                buttonContainer.innerHTML = `
                    <button type="button" id="retire-selected-btn" class="custom-action-button">
                        退社処理
                    </button>
                `;
                console.log('[DEBUG] 활성 직원 버튼 생성: 退社処理');
            }
            
            actionRow.appendChild(buttonContainer);
            console.log('[DEBUG] 버튼 컨테이너 추가 완료');
            
            // 버튼 이벤트 리스너 추가
            setTimeout(() => {
                const retireBtn = document.getElementById('retire-selected-btn');
                const deleteBtn = document.getElementById('delete-selected-btn');
                const restoreBtn = document.getElementById('restore-selected-btn');
                
                console.log('[DEBUG] 버튼 찾기 결과:', {
                    retireBtn: retireBtn,
                    deleteBtn: deleteBtn,
                    restoreBtn: restoreBtn
                });
                
                if (retireBtn) {
                    retireBtn.addEventListener('click', function() {
                        const selectedIds = getSelectedIds();
                        if (selectedIds.length === 0) {
                            alert('従業員を選択してください。');
                            return;
                        }
                        
                        if (confirm('選択された従業員を退社処理しますか？')) {
                            performAction('retire_selected', selectedIds);
                        }
                    });
                    console.log('[DEBUG] 퇴사 처리 버튼 이벤트 등록');
                }
                
                if (deleteBtn) {
                    deleteBtn.addEventListener('click', function() {
                        const selectedIds = getSelectedIds();
                        if (selectedIds.length === 0) {
                            alert('従業員を選択してください。');
                            return;
                        }
                        
                        if (confirm('選択された従業員を完全に削除しますか？この操作は取り消せません。')) {
                            performAction('delete_selected', selectedIds);
                        }
                    });
                    console.log('[DEBUG] 삭제 버튼 이벤트 등록');
                }
                
                if (restoreBtn) {
                    restoreBtn.addEventListener('click', function() {
                        const selectedIds = getSelectedIds();
                        if (selectedIds.length === 0) {
                            alert('従業員を選択してください。');
                            return;
                        }
                        
                        if (confirm('選択された従業員を復元しますか？')) {
                            performAction('restore_selected', selectedIds);
                        }
                    });
                    console.log('[DEBUG] 복원 버튼 이벤트 등록');
                }
            }, 100);
        }
    });

    // 선택된 체크박스 ID들 가져오기
    function getSelectedIds() {
        const checkboxes = document.querySelectorAll('input[name="_selected_action"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    // 액션 수행
    function performAction(action, ids) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = window.location.href;

        // CSRF 토큰 추가
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);

        // 액션 선택
        const actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = action;
        form.appendChild(actionInput);

        // 선택된 ID들 추가
        ids.forEach(id => {
            const idInput = document.createElement('input');
            idInput.type = 'hidden';
            idInput.name = '_selected_action';
            idInput.value = id;
            form.appendChild(idInput);
        });

        document.body.appendChild(form);
        form.submit();
    }
    
    console.log('[DEBUG] initCustomAdmin 완료');
}

// 여러 방법으로 실행 시도
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCustomAdmin);
} else {
    initCustomAdmin();
}

// 추가로 window.onload도 시도
window.addEventListener('load', function() {
    console.log('[DEBUG] window.load 실행됨');
    setTimeout(initCustomAdmin, 500);
});

// 즉시 실행도 시도
setTimeout(initCustomAdmin, 100); 