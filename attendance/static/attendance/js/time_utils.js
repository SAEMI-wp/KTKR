/**
 * 時間入力関連のユーティリティ関数
 */

// 開始時刻 "現在" ボタン クリック時: 開始時刻に現在時刻 + 通常 ボタンと同じロジックで終了時刻を設定
function setCurrentTimeForStartTime(startTimeInputId, endTimeInputId) {
    const startInput = document.getElementById(startTimeInputId);
    const endInput = document.getElementById(endTimeInputId);
    
    if (!startInput || !endInput) return;　// 開始時刻と終了時刻が存在しない場合は処理を終了
    
    // 現在の時刻を取得
    const now = new Date();
    const currentHours = String(now.getHours()).padStart(2, '0');
    const currentMinutes = String(now.getMinutes()).padStart(2, '0');
    const currentTime = `${currentHours}:${currentMinutes}`;
    
    // 開始時刻に現在時刻を設定
    startInput.value = currentTime;
    startInput.dispatchEvent(new Event('change', { bubbles: true }));
    
    // 通常 ボタンと同じロジックで終了時刻を設定
    // 月別データの基準カレンダーを確認 (通常 ボタンから取得したロジック)
    const normalHoursBtn = document.getElementById('normal-hours-btn');
    let endTime;
    
    if (normalHoursBtn && normalHoursBtn.dataset.baseCalendar === 'H大甕') {
        // H大甕 캘린더: 고정 종료시간 17:10
        endTime = '17:10';
        console.log(`[DEBUG] H大甕 캘린더: 시작시간 ${currentTime} -> 종료시간 고정: ${endTime}`);
    } else {
        // 기준 캘린더: 고정 종료시간 18:00
        endTime = '18:00';
        console.log(`[DEBUG] 기준 캘린더: 시작시간 ${currentTime} -> 종료시간 고정: ${endTime}`);
    }
    
    // 종료시간 설정
    endInput.value = endTime;
    endInput.dispatchEvent(new Event('change', { bubbles: true }));
    
    // 시각적 피드백
    showTimeSetFeedback(startInput);
    showTimeSetFeedback(endInput);
    
    console.log(`[DEBUG] 시작시간 현재시간 설정 완료: ${currentTime} -> 종료시간: ${endTime}`);
}

// 종료시간 "現在" 버튼 클릭 시: 종료시간에만 현재시간 입력
function setCurrentTimeForEndTime(endTimeInputId) {
    const endInput = document.getElementById(endTimeInputId);
    
    if (!endInput) return;
    
    // 현재 시간 가져오기
    const now = new Date();
    const currentHours = String(now.getHours()).padStart(2, '0');
    const currentMinutes = String(now.getMinutes()).padStart(2, '0');
    const currentTime = `${currentHours}:${currentMinutes}`;
    
    // 종료시간에만 현재시간 설정
    endInput.value = currentTime;
    endInput.dispatchEvent(new Event('change', { bubbles: true }));
    
    // 시각적 피드백
    showTimeSetFeedback(endInput);
    
    console.log(`[DEBUG] 종료시간 현재시간 설정: ${currentTime}`);
}

// 기존 함수명과의 호환성을 위한 별칭 (하위 호환성)
function setCurrentTime(inputId) {
    // inputId가 start_time인지 end_time인지 판단
    if (inputId.includes('start_time')) {
        // 시작시간인 경우, 通常 버튼과 동일한 로직으로 종료시간도 함께 계산
        const endTimeId = inputId.replace('start_time', 'end_time');
        setCurrentTimeForStartTime(inputId, endTimeId);
    } else if (inputId.includes('end_time')) {
        // 종료시간인 경우, 종료시간만 설정
        setCurrentTimeForEndTime(inputId);
    } else {
        // 기본 동작 (기존 호환성)
        const input = document.getElementById(inputId);
        if (input) {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const currentTime = `${hours}:${minutes}`;
            
            input.value = currentTime;
            input.dispatchEvent(new Event('change', { bubbles: true }));
            showTimeSetFeedback(input);
        }
    }
}

// 시간 설정 완료 피드백 표시
function showTimeSetFeedback(input) {
    const originalBackground = input.style.backgroundColor;
    input.style.backgroundColor = '#d4edda';
    input.style.transition = 'background-color 0.3s ease';
    
    setTimeout(() => {
        input.style.backgroundColor = originalBackground;
    }, 500);
}

// 현재 시간을 가져오는 함수
function getCurrentTime() {
    const now = new Date();
    return {
        hours: String(now.getHours()).padStart(2, '0'),
        minutes: String(now.getMinutes()).padStart(2, '0'),
        time: `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    };
}

// 시간 형식 검증
function validateTimeFormat(timeString) {
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
    return timeRegex.test(timeString);
}

// 시작 시간과 종료 시간 비교
function validateTimeRange(startTime, endTime) {
    if (!startTime || !endTime) return true; // 둘 중 하나라도 비어있으면 검증 통과
    
    const start = new Date(`2000-01-01T${startTime}`);
    const end = new Date(`2000-01-01T${endTime}`);
    
    return end > start;
}

// 시간 차이 계산 (분 단위)
function calculateTimeDifference(startTime, endTime) {
    if (!startTime || !endTime) return 0;
    
    const start = new Date(`2000-01-01T${startTime}`);
    const end = new Date(`2000-01-01T${endTime}`);
    
    const diffMs = end - start;
    return Math.floor(diffMs / (1000 * 60)); // 분 단위로 반환
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('時間入力フィールドが準備されました');
    
    // 모든 시간 입력 필드에 이벤트 리스너 추가
    const timeInputs = document.querySelectorAll('input[type="time"]');
    timeInputs.forEach(input => {
        // 입력값 변경 시 검증
        input.addEventListener('change', function() {
            validateTimeInput(this);
        });
        
        // 포커스 시 현재 시간 표시 (선택사항)
        input.addEventListener('focus', function() {
            showCurrentTimeHint(this);
        });
    });
});

// 시간 입력 필드 검증
function validateTimeInput(input) {
    const timeValue = input.value;
    
    if (timeValue && !validateTimeFormat(timeValue)) {
        input.setCustomValidity('올바른 시간 형식을 입력해주세요 (HH:MM)');
        input.reportValidity();
    } else {
        input.setCustomValidity('');
    }
}

// 전역 함수로 노출
window.setCurrentTime = setCurrentTime;
window.setCurrentTimeForStartTime = setCurrentTimeForStartTime;
window.setCurrentTimeForEndTime = setCurrentTimeForEndTime;
window.getCurrentTime = getCurrentTime;
window.validateTimeFormat = validateTimeFormat;
window.validateTimeRange = validateTimeRange;
window.calculateTimeDifference = calculateTimeDifference;
