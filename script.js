/* script.js
  웹사이트의 모든 동작을 제어합니다.
*/

// --- (가짜 백엔드 API 함수) ---
// 프론트엔드 개발자는 이 함수들을 실제 fetch/axios로 교체하면 됩니다.

/**
 * (가짜) 파일을 백엔드에 업로드하고 작업 ID를 받습니다.
 * @param {File} file - 업로드할 파일
 * @returns {Promise<string>} - 작업 Task ID
 */
function apiUploadFile(file) {
    console.log("API CALL: /uploadfile", file.name);
    return new Promise(resolve => {
        setTimeout(() => {
            resolve("task-id-12345"); // 0.5초 후 가짜 작업 ID 반환
        }, 500);
    });
}

/**
 * (가짜) 작업 ID로 백엔드에 처리 상태를 묻습니다 (Polling).
 * @param {string} taskId - 작업 ID
 * @returns {Promise<object>} - 작업 상태 및 결과
 */
function apiGetTaskStatus(taskId) {
    console.log("API CALL: /tasks/", taskId);
    return new Promise(resolve => {
        setTimeout(() => {
            // (실제로는 여기서 status가 "SUCCESS"가 될 때까지 반복 호출합니다)
            resolve({
                task_id: taskId,
                status: "SUCCESS",
                result: { // 2.html(결과) 시안에 있던 데이터
                    "document_type": "Invoice (99.2%)",
                    "structured_data": {
                        "vendor": "CDG",
                        "invoice_number": "INV-2023-015",
                        "date": "2023-10-26",
                        "total_amount": 7500.00
                    },
                    "pii_detected": "2 items masked: ***-**-****"
                }
            });
        }, 2500); // 2.5초 후 가짜 성공 응답 반환 (로딩 시간 0.5 + 2.5 = 3초)
    });
}

/**
 * (가짜) 하이브리드 검색 API를 호출합니다.
 * @param {string} query - 검색어
 * @returns {Promise<object>} - 검색 결과
 */
function apiHybridSearch(query) {
    console.log("API CALL: /hybrid_search?q=", query);
    return new Promise(resolve => {
        setTimeout(() => {
            resolve({ // 4.html(검색) 시안에 있던 데이터
                "exact_matches": [
                    { "filename": "Client_Contract_Alpha.pdf", "type": "Contract", "snippet": "...our standard <mark>payment terms</mark> are Net 30..." },
                    { "filename": "Q4_Financial_Report.pdf", "type": "Report", "snippet": "...the section on <mark>payment terms</mark> clearly outlines..." }
                ],
                "semantic_matches": [
                    { "filename": "Invoice_Processing_SOP.pdf", "type": "Policy", "snippet": "This document outlines the standard operating procedure for handling incoming invoices..." },
                    { "filename": "Accounts_Payable_Guide.docx", "type": "Guide", "snippet": "A comprehensive guide for the AP team on managing billing cycles..." }
                ]
            });
        }, 1000); // 1초 후 가짜 검색 결과 반환
    });
}
// --- (가짜 백엔드 API 함수 끝) ---


// DOM(문서)이 모두 로드되면 이 함수를 실행합니다.
document.addEventListener("DOMContentLoaded", () => {
    
    // --- 페이지 공통 (검색) 로직 ---
    const searchForm = document.getElementById("search-form");
    const searchInput = document.getElementById("search-input");

    if (searchForm) {
        searchForm.addEventListener("submit", (event) => {
            event.preventDefault(); // 폼 제출 시 새로고침 방지
            const query = searchInput.value.trim();
            
            if (query) {
                // search.html 페이지로 검색어를 붙여서 이동시킵니다.
                window.location.href = `search.html?q=${encodeURIComponent(query)}`;
            }
        });
    }

    // --- 1. index.html (메인 페이지) 로직 ---
    const uploadButton = document.getElementById("select-file-button");
    
    if (uploadButton) {
        // 교체할 오른쪽 패널 3개를 모두 찾습니다.
        const panelEmpty = document.getElementById("right-panel-empty");
        const panelLoading = document.getElementById("right-panel-loading");
        const panelResult = document.getElementById("right-panel-result");

        // '파일 선택' 버튼 클릭 시 가짜 파일 인풋을 생성해 클릭합니다.
        uploadButton.addEventListener("click", () => {
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.onchange = (e) => { 
                const file = e.target.files[0];
                if (file) {
                    handleFileUpload(file); 
                }
            };
            fileInput.click();
        });
        
        async function handleFileUpload(file) {
            // 1. 빈 화면과 결과 화면을 숨깁니다.
            panelEmpty.classList.add("hidden");
            panelResult.classList.add("hidden");
            
            // 2. '로딩' 화면을 보여줍니다.
            panelLoading.classList.remove("hidden");
            panelLoading.classList.add("flex"); // hidden은 flex도 덮어쓰므로 flex를 다시 켜줍니다.

            try {
                // 3. (실제 API 호출) 파일 업로드 후 작업 ID 받기
                const taskId = await apiUploadFile(file);
                
                // 4. (실제 API 호출) 작업이 끝날 때까지 결과 Polling
                // (데모에서는 간단히 한 번만 호출합니다)
                const resultData = await apiGetTaskStatus(taskId);

                // 5. '결과' 화면을 데이터로 채우고 보여줍니다.
                if (resultData.status === "SUCCESS") {
                    const result = resultData.result;
                    
                    // (실제 데이터로 UI 업데이트)
                    panelResult.querySelector("h3:nth-of-type(1) + p").textContent = result.document_type;
                    panelResult.querySelector("#json-result-data code").textContent = JSON.stringify(result.structured_data, null, 2);
                    panelResult.querySelector("h3:nth-of-type(3) + div p").innerHTML = `${result.pii_detected}`;

                    // 6. 로딩 숨기고 결과 표시
                    panelLoading.classList.add("hidden");
                    panelLoading.classList.remove("flex");
                    panelResult.classList.remove("hidden");
                    panelResult.classList.add("flex");
                } else {
                    // (에러 처리)
                    throw new Error("Task failed");
                }
            } catch (error) {
                console.error("Upload failed:", error);
                // 에러 발생 시 '빈 화면'으로 복귀
                panelLoading.classList.add("hidden");
                panelLoading.classList.remove("flex");
                panelEmpty.classList.remove("hidden");
                panelEmpty.classList.add("flex");
                alert("File processing failed. Please try again.");
            }
        }
    }

    // --- 2. search.html (검색 페이지) 로직 ---
    const keywordResultsContainer = document.getElementById("keyword-results");
    
    if (keywordResultsContainer) {
        // 페이지 URL에서 'q' 파라미터(검색어)를 가져옵니다.
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');

        if (query) {
            // 1. 검색창에 현재 검색어를 채워넣습니다.
            if (searchInput) searchInput.value = query;
            document.getElementById("search-results-summary").textContent = `Showing results for '${query}'`;
            
            // 2. (실제 API 호출)
            apiHybridSearch(query).then(results => {
                // 3. 키워드 검색 결과 채우기
                const kwContainer = document.getElementById("keyword-results");
                kwContainer.innerHTML = ""; // 기존 결과 비우기
                results.exact_matches.forEach(doc => {
                    kwContainer.innerHTML += `
                        <div class="bg-surface-light dark:bg-surface-dark p-4 rounded-lg border border-border-light dark:border-border-dark">
                            <p class="font-medium text-primary">${doc.filename}</p>
                            <span class="text-xs font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 px-2 py-0.5 rounded-full">${doc.type}</span>
                            <p class="mt-2 text-sm text-text-secondary-light dark:text-text-secondary-dark">${doc.snippet}</p>
                        </div>
                    `;
                });

                // 4. 시맨틱 검색 결과 채우기
                const semContainer = document.getElementById("semantic-results");
                semContainer.innerHTML = ""; // 기존 결과 비우기
                results.semantic_matches.forEach(doc => {
                    semContainer.innerHTML += `
                        <div class="bg-surface-light dark:bg-surface-dark p-4 rounded-lg border border-border-light dark:border-border-dark">
                            <p class="font-medium text-primary">${doc.filename}</p>
                            <span class="text-xs font-medium bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 px-2 py-0.5 rounded-full">${doc.type}</span>
                            <p class="mt-2 text-sm text-text-secondary-light dark:text-text-secondary-dark">${doc.snippet}</p>
                        </div>
                    `;
                });
            });
        } else {
             document.getElementById("search-results-summary").textContent = "Please enter a search term.";
        }
    }
});