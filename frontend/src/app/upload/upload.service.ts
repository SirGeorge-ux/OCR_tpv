import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UploadRecord {
    id: number;
    original_name: string;
    stored_name: string;
    file_path: string;
    url: string;
    mime_type: string | null;
    size_bytes: number;
    created_at: string;

    ocr_status: string | null;
    ocr_processed_at: string | null;
    ocr_error: string | null;

    raw_text: string | null;
    line_count: number | null;
    avg_confidence: number | null;
    parsed_name: string | null;
    parsed_phone: string | null;
    phone_candidates: string[];
    name_candidates: string[];
}

export interface ProcessPendingResponse {
    processed_count: number;
    items: UploadRecord[];
}

@Injectable({
    providedIn: 'root',
})
export class UploadService {
    private readonly http = inject(HttpClient);
    private readonly apiUrl = 'http://localhost:8000';

    upload(file: File): Observable<UploadRecord> {
        const formData = new FormData();
        formData.append('file', file);

        return this.http.post<UploadRecord>(`${this.apiUrl}/uploads`, formData);
    }

    list(): Observable<UploadRecord[]> {
        return this.http.get<UploadRecord[]>(`${this.apiUrl}/uploads`);
    }

    processOne(id: number): Observable<UploadRecord> {
        return this.http.post<UploadRecord>(`${this.apiUrl}/uploads/${id}/process`, {});
    }

    processPending(): Observable<ProcessPendingResponse> {
        return this.http.post<ProcessPendingResponse>(`${this.apiUrl}/uploads/process-pending`, {});
    }
}