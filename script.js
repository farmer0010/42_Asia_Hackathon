/* script.js
   웹사이트의 모든 동작을 제어합니다.
   - (수정) 가짜 API 함수를 실제 백엔드 연동 코드로 교체했습니다.
   - (수정) Polling 로직을 추가했습니다.
   - (수정) 백엔드/프론트엔드 스키마 불일치 문제를 해결했습니다.
*/

// --- (실제 백엔드 API 함수) ---
const BACKEND_URL = "http://localhost:8001"; // FastAPI 서버 주소

/**
 * (수정) 파일을 실제 백엔드에 업로드하고 작업 ID를 받습니다.
 * @param {File} file - 업로드할 파일
 * @returns {Promise<string>} - 작업 Task ID
 */
async function apiUploadFile(file) {
    console.log("API CALL: POST /uploadfile/", file.name);
    const formData = new FormData();
    // 백엔드 main.py의 `file: UploadFile` 파라미터 이름과 일치해야 합니다.
    formData.append("file", file);

    const response = await fetch(`${BACKEND_URL}/uploadfile/`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json();
        console.error("Upload failed response:", errorData);
        throw new Error(`Upload failed: ${errorData.detail || response.statusText}`);
    }

    const data = await response.json(); // 백엔드로부터 {"task_id": "..."} 수신
    return data.task_id; // `handleFileUpload`가 기대하는 문자열 ID 반환
}

// Polling을 위한 sleep 헬퍼 함수
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * (수정) 작업 ID로 백엔드에 처리 상태를 묻습니다 (Polling).
 * @param {string} taskId - 작업 ID
 * @returns {Promise<object>} - 작업 상태 및 결과 (성공 또는 실패 시)
 */
async function apiGetTaskStatus(taskId) {
    console.log("API CALL: GET /tasks/", taskId);

    while (true) {
        const response = await fetch(`${BACKEND_URL}/tasks/${taskId}`);
        if (!response.ok) {
            const errorData = await response.json();
            console.error("Task status failed response:", errorData);
            throw new Error(`Task status check failed: ${errorData.detail || response.statusText}`);
        }

        const data = await response.json(); // {"task_id": ..., "status": ..., "result": ...}

        if (data.status === "SUCCESS") {
            console.log("Task SUCCESS", data.result);
            return data; // 최종 성공 결과 반환
        }

        if (data.status === "FAILURE") {
            console.error("Task FAILED", data.result);
            throw new Error("Task processing failed on the backend.");
        }

        // (설명)
        // Spring @Async와 유사하게, Celery 작업이 아직 "PENDING" 상태이면
        // 클라이언트(여기)가 잠시 대기한 후 다시 상태를 확인해야 합니다.
        console.log("Task PENDING, polling again in 2 seconds...");
        await sleep(2000); // 2초 대기 후 while 루프 다시 시작
    }
}

/**
 * (수정) 실제 하이브리드 검색 API를 호출합니다.
 * @param {string} query - 검색어
 * @returns {Promise<object>} - 검색 결과
 */
async function apiHybridSearch(query) {
    console.log("API CALL: GET /search?q=", query);
    
    // 백엔드 main.py의 `q: str` 쿼리 파라미터로 전송
    const response = await fetch(`${BACKEND_URL}/search?q=${encodeURIComponent(query)}`);
    
    if (!response.ok) {
        const errorData = await response.json();
        console.error("Search failed response:", errorData);
        throw new Error(`Search failed: ${errorData.detail || response.statusText}`);
    }
    
    const data = await response.json(); // {"exact_matches": [...], "semantic_matches": [...]}
    return data;
}
// --- (실제 백엔드 API 함수 끝) ---


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
                // (수정) apiGetTaskStatus가 이제 Polling을 내장하고 있으므로,
                // 이 함수는 'SUCCESS' 또는 'FAILURE'시에만 반환됩니다.
                const resultData = await apiGetTaskStatus(taskId);

                // 5. '결과' 화면을 데이터로 채우고 보여줍니다.
                if (resultData.status === "SUCCESS") {
                    const result = resultData.result; // (중요) 백엔드의 PipelineResult 스키마
                    
                    // --- (수정) 백엔드-프론트엔드 스키마 매핑 ---
                    
                    // 1. Document Type: 백엔드(doc_type, confidence) -> 프론트엔드("Invoice (99.2%)")
                    const docType = result.doc_type || "Unknown";
                    const confidence = (result.confidence || 0) * 100;
                    const formattedDocType = `${docType.charAt(0).toUpperCase() + docType.slice(1)} (${confidence.toFixed(1)}%)`;
                    panelResult.querySelector("h3:nth-of-type(1) + p").textContent = formattedDocType;

                    // 2. Structured Data: 스키마 동일 (structured_data)
                    panelResult.querySelector("#json-result-data code").textContent = JSON.stringify(result.structured_data || { "message": "No data extracted." }, null, 2);

                    // 3. PII: 백엔드(pii_details) -> 프론트엔드(pii_detected 문자열)
                    const piiInfo = result.pii_details;
                    let piiHtml = '<span class="text-green-600">No PII detected.</span>';
                    const piiTextElement = panelResult.querySelector("h3:nth-of-type(3) + div p");
                    const piiIconElement = panelResult.querySelector("h3:nth-of-type(3) + div span.material-symbols-outlined");

                    if (piiInfo && piiInfo.count > 0) {
                        // 프론트엔드 HTML 시안과 유사하게 구성
                        piiHtml = `${piiInfo.count} items masked: <code class="bg-border-light dark:bg-border-dark px-1.5 py-0.5 rounded text-xs">[Masked]</code>`;
                        piiIconElement.classList.add("text-yellow-600");
                        piiIconElement.classList.remove("text-green-600");
                        piiIconElement.textContent = "warning";
                    } else {
                        piiIconElement.classList.add("text-green-600");
                        piiIconElement.classList.remove("text-yellow-600");
                        piiIconElement.textContent = "check_circle"; // 'check' 아이콘
                    }
                    piiTextElement.innerHTML = piiHtml;
                    // --- 스키마 매핑 끝 ---

                    // 6. 로딩 숨기고 결과 표시
                    panelLoading.classList.add("hidden");
                    panelLoading.classList.remove("flex");
                    panelResult.classList.remove("hidden");
                    panelResult.classList.add("flex");
                } else {
                    // (에러 처리) apiGetTaskStatus가 FAILED 상태를 throw하므로
                    // 이 else 블록은 사실상 도달하지 않지만, 안전을 위해 남겨둡니다.
                    throw new Error(resultData.status || "Task failed without specific status.");
                }
            } catch (error) {
                console.error("Upload failed:", error);
                // 에러 발생 시 '빈 화면'으로 복귀
                panelLoading.classList.add("hidden");
                panelLoading.classList.remove("flex");
                panelEmpty.classList.remove("hidden");
                panelEmpty.classList.add("flex");
                alert(`File processing failed: ${error.message}`);
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
                
                if (results.exact_matches.length === 0) {
                    kwContainer.innerHTML = `<p class="text-text-secondary-light dark:text-text-secondary-dark">No exact matches found.</p>`;
                } else {
                    results.exact_matches.forEach(doc => {
                        // (수정) 스키마 불일치 해결: doc.type -> doc.doc_type
                        kwContainer.innerHTML += `
                            <div class="bg-surface-light dark:bg-surface-dark p-4 rounded-lg border border-border-light dark:border-border-dark">
                                <p class="font-medium text-primary">${doc.filename}</p>
                                <span class="text-xs font-medium bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 px-2 py-0.5 rounded-full">${doc.doc_type || 'Unknown'}</span>
                                <p class="mt-2 text-sm text-text-secondary-light dark:text-text-secondary-dark">${doc.snippet}</p>
                            </div>
                        `;
                    });
                }

                // 4. 시맨틱 검색 결과 채우기
                const semContainer = document.getElementById("semantic-results");
                semContainer.innerHTML = ""; // 기존 결과 비우기

                if (results.semantic_matches.length === 0) {
                    semContainer.innerHTML = `<p class="text-text-secondary-light dark:text-text-secondary-dark">No semantic matches found.</p>`;
                } else {
                    results.semantic_matches.forEach(doc => {
                        // (수정) 스키마 불일치 해결: doc.type -> doc.doc_type
                        semContainer.innerHTML += `
                            <div class="bg-surface-light dark:bg-surface-dark p-4 rounded-lg border border-border-light dark:border-border-dark">
                                <p class="font-medium text-primary">${doc.filename}</p>
                                <span class="text-xs font-medium bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 px-2 py-0.5 rounded-full">${doc.doc_type || 'Unknown'}</span>
                                <p class="mt-2 text-sm text-text-secondary-light dark:text-text-secondary-dark">${doc.snippet}</p>
                            </div>
                        `;
                    });
                }
            }).catch(error => {
                console.error("Search failed:", error);
                document.getElementById("search-results-summary").textContent = `Search failed: ${error.message}`;
            });
        } else {
             document.getElementById("search-results-summary").textContent = "Please enter a search term.";
        }
    }
});