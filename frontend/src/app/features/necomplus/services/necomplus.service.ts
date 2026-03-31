import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
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
}

export interface NecomplusProcessResponse {
    plantilla: string;
    upload_comercio_id: number;
    upload_detalle_id: number;
    comercio_data: {
        descripcion: string | null;
        codigo_comercio: string | null;
        direccion: string | null;
        localidad: string | null;
        provincia: string | null;
        cod_postal: string | null;
        telefono_1: string | null;
        telefono_2: string | null;
        horario: string | null;
        contacto: string | null;
    };
    detalle_data: {
        interv: string | null;
        ns_ret_afec: string | null;
    };
    ocr_confidence_comercio: number | null;
    ocr_confidence_detalle: number | null;
    estado_comercio: {
        action: string;
        row: NecomplusCommerceSummary;
    };
}

export interface NecomplusCommerceSummary {
    id: number;
    codigo_comercio: string;
    descripcion: string | null;
    direccion: string | null;
    localidad: string | null;
    provincia: string | null;
    cod_postal: string | null;
    telefono_1: string | null;
    telefono_2: string | null;
    horario: string | null;
    contacto: string | null;
    ns_inst_actual: string | null;
    ultimo_ns_ret_afec: string | null;
    ultima_interv: string | null;
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

export interface NecomplusContact {
    id: number;
    nombre: string;
    orden: number;
    created_at: string;
    updated_at: string;
}

export interface NecomplusCommerceDetail extends NecomplusCommerceSummary {
    contactos_manuales: NecomplusContact[];
}

export interface NecomplusManualPayload {
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
}

@Injectable({
    providedIn: 'root',
})
export class NecomplusService {
    private readonly http = inject(HttpClient);
    private readonly apiUrl = 'http://localhost:8000';

    upload(file: File): Observable<UploadRecord> {
        const formData = new FormData();
        formData.append('file', file);

        return this.http.post<UploadRecord>(`${this.apiUrl}/uploads`, formData);
    }

    uploadWithProgress(file: File): Observable<HttpEvent<UploadRecord>> {
        const formData = new FormData();
        formData.append('file', file);

        return this.http.post<UploadRecord>(`${this.apiUrl}/uploads`, formData, {
            observe: 'events',
            reportProgress: true,
        });
    }

    processPair(uploadComercioId: number, uploadDetalleId: number): Observable<NecomplusProcessResponse> {
        return this.http.post<NecomplusProcessResponse>(`${this.apiUrl}/necomplus/process-pair`, {
            upload_comercio_id: uploadComercioId,
            upload_detalle_id: uploadDetalleId,
        });
    }

    listComercios(): Observable<NecomplusCommerceSummary[]> {
        return this.http.get<NecomplusCommerceSummary[]>(`${this.apiUrl}/necomplus/comercios`);
    }

    getComercio(comercioId: number): Observable<NecomplusCommerceDetail> {
        return this.http.get<NecomplusCommerceDetail>(`${this.apiUrl}/necomplus/comercios/${comercioId}`);
    }

    updateManual(comercioId: number, payload: NecomplusManualPayload): Observable<NecomplusCommerceDetail> {
        return this.http.put<NecomplusCommerceDetail>(
            `${this.apiUrl}/necomplus/comercios/${comercioId}/manual`,
            payload
        );
    }
}