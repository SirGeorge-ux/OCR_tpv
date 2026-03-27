import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { ProcessPendingResponse, UploadRecord, UploadService } from '../upload.service';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="card">
      <h2>Subir capturas</h2>

      <input
        id="fileInput"
        type="file"
        multiple
        accept="image/png,image/jpeg,image/webp"
        (change)="onFileChange($event)"
      />

      <div class="actions">
        <button (click)="uploadAll()" [disabled]="uploading || !selectedFiles.length">
          {{ uploading ? 'Subiendo...' : 'Subir imágenes' }}
        </button>

        <button (click)="processPending()" [disabled]="processingPending || !uploads.length">
          {{ processingPending ? 'Procesando...' : 'Procesar pendientes' }}
        </button>

        <button (click)="loadUploads()" [disabled]="loadingList">
          {{ loadingList ? 'Actualizando...' : 'Recargar listado' }}
        </button>
      </div>

      <div *ngIf="selectedFiles.length" class="info">
        <strong>Archivos seleccionados:</strong>
        <ul>
          <li *ngFor="let file of selectedFiles">
            {{ file.name }} ({{ formatBytes(file.size) }})
          </li>
        </ul>
      </div>

      <p *ngIf="statusMessage" class="ok">{{ statusMessage }}</p>
      <p *ngIf="errorMessage" class="error">{{ errorMessage }}</p>
    </section>

    <section class="card">
      <h2>Últimas subidas</h2>

      <div *ngIf="loadingList">Cargando registros...</div>

      <div *ngIf="!loadingList && !uploads.length">
        Todavía no hay archivos subidos.
      </div>

      <ul *ngIf="uploads.length" class="upload-list">
        <li *ngFor="let item of uploads">
          <div class="row top-row">
            <div>
              <strong>{{ item.original_name }}</strong>
              <div class="meta">
                {{ item.mime_type || 'sin mime' }} · {{ formatBytes(item.size_bytes) }}
              </div>
              <div class="meta">
                Subido: {{ item.created_at | date:'dd/MM/yyyy HH:mm:ss' }}
              </div>
              <div class="meta">
                Estado OCR:
                <span [class]="statusClass(item.ocr_status)">{{ item.ocr_status || 'pending' }}</span>
              </div>
            </div>

            <div class="right actions-inline">
              <a [href]="item.url" target="_blank" rel="noopener noreferrer">Ver imagen</a>

              <button
                class="small"
                (click)="processOne(item)"
                [disabled]="item.ocr_status === 'processing'"
              >
                {{ item.ocr_status === 'processing' ? 'Procesando...' : 'Procesar OCR' }}
              </button>
            </div>
          </div>

          <div class="result-box">
            <div><strong>Teléfono detectado:</strong> {{ item.parsed_phone || 'No detectado' }}</div>
            <div><strong>Nombre detectado:</strong> {{ item.parsed_name || 'No detectado' }}</div>
            <div><strong>Líneas OCR:</strong> {{ item.line_count ?? 0 }}</div>
            <div><strong>Confianza media:</strong> {{ formatConfidence(item.avg_confidence) }}</div>

            <div *ngIf="item.phone_candidates?.length" class="candidate-block">
              <strong>Teléfonos candidatos:</strong>
              <span>{{ item.phone_candidates.join(', ') }}</span>
            </div>

            <div *ngIf="item.name_candidates?.length" class="candidate-block">
              <strong>Nombres candidatos:</strong>
              <span>{{ item.name_candidates.join(' | ') }}</span>
            </div>

            <div *ngIf="item.raw_text" class="raw-text">
              <strong>Texto OCR:</strong>
              <pre>{{ item.raw_text }}</pre>
            </div>

            <div *ngIf="item.ocr_error" class="error">
              <strong>Error OCR:</strong> {{ item.ocr_error }}
            </div>
          </div>
        </li>
      </ul>
    </section>
  `,
  styles: [`
    .card {
      border: 1px solid #ddd;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      background: #fff;
    }

    h2 {
      margin-top: 0;
    }

    .actions {
      display: flex;
      gap: 12px;
      margin: 16px 0;
      flex-wrap: wrap;
    }

    .actions-inline {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }

    button {
      padding: 10px 16px;
      border: 0;
      border-radius: 8px;
      cursor: pointer;
      background: #111827;
      color: white;
    }

    .small {
      padding: 8px 12px;
      font-size: 14px;
    }

    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .info {
      margin-top: 12px;
    }

    .ok {
      color: #166534;
      font-weight: 600;
    }

    .error {
      color: #b91c1c;
      font-weight: 600;
    }

    .upload-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .upload-list li {
      border-top: 1px solid #eee;
      padding: 18px 0;
    }

    .upload-list li:first-child {
      border-top: 0;
      padding-top: 0;
    }

    .top-row {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
    }

    .meta {
      color: #666;
      font-size: 14px;
      margin-top: 4px;
    }

    .right a {
      text-decoration: none;
      font-weight: 600;
    }

    .result-box {
      margin-top: 14px;
      padding: 14px;
      border-radius: 10px;
      background: #f9fafb;
      border: 1px solid #ececec;
      display: grid;
      gap: 8px;
    }

    .candidate-block {
      display: grid;
      gap: 4px;
    }

    .raw-text pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 6px 0 0;
      padding: 10px;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      max-height: 240px;
      overflow: auto;
    }

    .status-done {
      color: #166534;
      font-weight: 700;
    }

    .status-processing {
      color: #92400e;
      font-weight: 700;
    }

    .status-error {
      color: #b91c1c;
      font-weight: 700;
    }

    .status-pending {
      color: #1d4ed8;
      font-weight: 700;
    }
  `]
})
export class UploadComponent implements OnInit {
  private readonly uploadService = inject(UploadService);

  selectedFiles: File[] = [];
  uploads: UploadRecord[] = [];

  uploading = false;
  loadingList = false;
  processingPending = false;

  statusMessage = '';
  errorMessage = '';

  async ngOnInit(): Promise<void> {
    await this.loadUploads();
  }

  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFiles = input.files ? Array.from(input.files) : [];
    this.statusMessage = '';
    this.errorMessage = '';
  }

  async uploadAll(): Promise<void> {
    if (!this.selectedFiles.length) {
      this.errorMessage = 'Selecciona al menos una imagen.';
      return;
    }

    this.uploading = true;
    this.statusMessage = '';
    this.errorMessage = '';

    try {
      for (const file of this.selectedFiles) {
        await firstValueFrom(this.uploadService.upload(file));
      }

      this.statusMessage = `${this.selectedFiles.length} archivo(s) subido(s) correctamente.`;
      this.selectedFiles = [];

      const input = document.getElementById('fileInput') as HTMLInputElement | null;
      if (input) {
        input.value = '';
      }

      await this.loadUploads();
    } catch (error) {
      console.error(error);
      this.errorMessage = 'Ha fallado la subida de uno o más archivos.';
    } finally {
      this.uploading = false;
    }
  }

  async processOne(item: UploadRecord): Promise<void> {
    this.statusMessage = '';
    this.errorMessage = '';

    try {
      await firstValueFrom(this.uploadService.processOne(item.id));
      this.statusMessage = `OCR ejecutado sobre: ${item.original_name}`;
      await this.loadUploads();
    } catch (error) {
      console.error(error);
      this.errorMessage = `No se pudo procesar el OCR de ${item.original_name}.`;
      await this.loadUploads();
    }
  }

  async processPending(): Promise<void> {
    this.processingPending = true;
    this.statusMessage = '';
    this.errorMessage = '';

    try {
      const response: ProcessPendingResponse = await firstValueFrom(this.uploadService.processPending());
      this.statusMessage = `Procesadas ${response.processed_count} imagen(es).`;
      await this.loadUploads();
    } catch (error) {
      console.error(error);
      this.errorMessage = 'Ha fallado el procesamiento masivo.';
      await this.loadUploads();
    } finally {
      this.processingPending = false;
    }
  }

  async loadUploads(): Promise<void> {
    this.loadingList = true;

    try {
      this.uploads = await firstValueFrom(this.uploadService.list());
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo cargar el listado de archivos.';
    } finally {
      this.loadingList = false;
    }
  }

  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    const value = bytes / Math.pow(1024, index);

    return `${value.toFixed(2)} ${units[index]}`;
  }

  formatConfidence(value: number | null): string {
    if (value === null || value === undefined) return 'N/D';
    return value.toFixed(4);
  }

  statusClass(status: string | null): string {
    switch (status) {
      case 'done':
        return 'status-done';
      case 'processing':
        return 'status-processing';
      case 'error':
        return 'status-error';
      default:
        return 'status-pending';
    }
  }
}