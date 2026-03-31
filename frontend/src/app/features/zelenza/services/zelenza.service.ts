import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';


export interface ZelenzaParsedResult {
    id: number;
    ot_id: string | null;
    entidad_bancaria: string | null;
    descripcion: string | null;
    poblacion: string | null;
    direccion: string | null;
    cod_postal: string | null;
    provincia: string | null;
    telefono_1: string | null;
    telefono_2: string | null;
    contacto: string | null;
    ref_cliente: string | null;
    num_comercio: string | null;
    horario: string | null;
    ns_inst: string | null;
    ns_ret_afec: string | null;
    ocr_confidence: number | null;
}

export interface UploadRecord {
    id: number;
    original_name: string;
    stored_name: string;
    file_path: string;
    url: string;
    mime_type: string | null;
    size_bytes: number;
    created_at: string;
    zelenza_result: ZelenzaParsedResult | null;
}

export interface ZelenzaProcessResponse {
    upload_id: number;
    plantilla: string;
    parsed: Omit<ZelenzaParsedResult, 'id' | 'ocr_confidence'>;
    raw_text: string;
    ocr_confidence: number | null;
    estado_comercio: {
        action: string;
        terminal_rotated?: boolean;
        row: ZelenzaCommerceSummary;
    };
}

export interface ZelenzaCommerceSummary {
    id: number;
    num_comercio: string;
    entidad_bancaria: string | null;
    descripcion: string | null;
    poblacion: string | null;
    direccion: string | null;
    cod_postal: string | null;
    provincia: string | null;
    telefono_1: string | null;
    telefono_2: string | null;
    contacto: string | null;
    horario: string | null;
    ns_inst_actual: string | null;
    ultimo_ns_ret_afec: string | null;
    ultimo_ot_id: string | null;
    ultimo_ref_cliente: string | null;
    ultimo_upload_id: number | null;
    sector: string | null;
    tipo: string | null;
    comentario: string | null;
    actuacion: number;
    coordenada_lat: number | null;
    coordenada_lng: number | null;
    geocoded_at: string | null;
    first_seen_at: string;
    last_extracted_at: string;
    created_at: string;
    updated_at: string;
}

export interface ZelenzaContact {
    id: number;
    nombre: string;
    orden: number;
    created_at: string;
    updated_at: string;
}

export interface ZelenzaCommerceDetail extends ZelenzaCommerceSummary {
    contactos_manuales: ZelenzaContact[];
}

export interface ZelenzaUploadDetail {
    id: number;
    upload_id: number;
    plantilla: string;
    ot_id: string | null;
    entidad_bancaria: string | null;
    descripcion: string | null;
    poblacion: string | null;
    direccion: string | null;
    cod_postal: string | null;
    provincia: string | null;
    telefono_1: string | null;
    telefono_2: string | null;
    contacto: string | null;
    ref_cliente: string | null;
    num_comercio: string | null;
    horario: string | null;
    ns_inst: string | null;
    ns_ret_afec: string | null;
    actuacion: number;
    raw_text: string | null;
    ocr_confidence: number | null;
    source_uploaded_at: string;
    extracted_at: string;
    created_at: string;
    updated_at: string;
}

@Injectable({
    providedIn: 'root',
})
export class ZelenzaService {
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

    processZelenza(uploadId: number): Observable<ZelenzaProcessResponse> {
        return this.http.post<ZelenzaProcessResponse>(
            `${this.apiUrl}/uploads/${uploadId}/process/zelenza`,
            {}
        );
    }

    getUploadZelenza(uploadId: number): Observable<ZelenzaUploadDetail> {
        return this.http.get<ZelenzaUploadDetail>(`${this.apiUrl}/uploads/${uploadId}/zelenza`);
    }

    listComercios(): Observable<ZelenzaCommerceSummary[]> {
        return this.http.get<ZelenzaCommerceSummary[]>(`${this.apiUrl}/zelenza/comercios`);
    }

    getComercio(comercioId: number): Observable<ZelenzaCommerceDetail> {
        return this.http.get<ZelenzaCommerceDetail>(`${this.apiUrl}/zelenza/comercios/${comercioId}`);
    }
    updateManual(comercioId: number, payload: {
        ns_inst_manual: string | null;
        sector: string | null;
        tipo: string | null;
        comentario: string | null;
        actuacion: number;
        coordenada_lat: number | null;
        coordenada_lng: number | null;
        geocoded_at: string | null;
        contactos: Array<{
            nombre: string;
            orden: number;
        }>;
    }): Observable<ZelenzaCommerceDetail> {
        return this.http.put<ZelenzaCommerceDetail>(
            `${this.apiUrl}/zelenza/comercios/${comercioId}/manual`,
            payload
        );
    }
    uploadWithProgress(file: File): Observable<HttpEvent<UploadRecord>> {
        const formData = new FormData();
        formData.append('file', file);

        return this.http.post<UploadRecord>(`${this.apiUrl}/uploads`, formData, {
            observe: 'events',
            reportProgress: true,
        });
    }
}