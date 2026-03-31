import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import {
  UploadRecord,
  ZelenzaService,
  ZelenzaCommerceDetail,
  ZelenzaCommerceSummary,
  ZelenzaProcessResponse,
  ZelenzaUploadDetail,
} from '../services/zelenza.service';
import {
  ManualCommerceFormComponent,
  ManualCommerceInitialData,
  ManualCommercePayload,
} from '../../../shared/components/manual-commerce-form/manual-commerce-form.component';

@Component({
  selector: 'app-zelenza-page',
  standalone: true,
  imports: [CommonModule, RouterLink, ManualCommerceFormComponent],
  templateUrl: './zelenza-page.component.html',
  styleUrl: './zelenza-page.component.css'
})

export class ZelenzaPageComponent implements OnInit {

  selectedFiles: File[] = [];
  uploads: UploadRecord[] = [];
  comercios: ZelenzaCommerceSummary[] = [];

  selectedUploadDetail: ZelenzaUploadDetail | null = null;
  selectedComercio: ZelenzaCommerceDetail | null = null;
  selectedProcessResult: ZelenzaProcessResponse | null = null;

  manualChoice: boolean | null = null;
  savingManual = false;
  manualInitialData: ManualCommerceInitialData | null = null;

  uploading = false;
  loadingList = false;
  loadingComercios = false;

  loadingUploadDetailId: number | null = null;
  loadingComercioDetailId: number | null = null;

  uploadProgress: number | null = null;
  currentUploadsPage = 1;
  uploadsPageSize = 5;
  showRawText = false;

  processingIds = new Set<number>();

  statusMessage = '';
  errorMessage = '';


  get totalUploadsPages(): number {
    return Math.max(1, Math.ceil(this.uploads.length / this.uploadsPageSize));
  }

  get visibleUploads(): UploadRecord[] {
    const start = (this.currentUploadsPage - 1) * this.uploadsPageSize;
    return this.uploads.slice(start, start + this.uploadsPageSize);
  }

  nextUploadsPage(): void {
    if (this.currentUploadsPage < this.totalUploadsPages) {
      this.currentUploadsPage++;
    }
  }

  prevUploadsPage(): void {
    if (this.currentUploadsPage > 1) {
      this.currentUploadsPage--;
    }
  }

  toggleRawText(): void {
    this.showRawText = !this.showRawText;
  }

  constructor(
    private readonly uploadService: ZelenzaService,
    private readonly cdr: ChangeDetectorRef,
  ) { }
  async ngOnInit(): Promise<void> {
    await this.reloadAll();
  }

  async reloadAll(): Promise<void> {
    await this.loadUploads();
    await this.loadComercios();
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
    this.uploadProgress = 0;
    this.statusMessage = '';
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      const totalFiles = this.selectedFiles.length;

      for (let index = 0; index < totalFiles; index++) {
        const file = this.selectedFiles[index];

        await new Promise<void>((resolve, reject) => {
          this.uploadService.uploadWithProgress(file).subscribe({
            next: (event) => {
              if (event.type === HttpEventType.UploadProgress) {
                const fileProgress = Math.round((event.loaded * 100) / (event.total ?? file.size ?? 1));
                const globalProgress = Math.round(((index + fileProgress / 100) / totalFiles) * 100);
                this.uploadProgress = globalProgress;
                this.cdr.detectChanges();
              }

              if (event.type === HttpEventType.Response) {
                const globalProgress = Math.round(((index + 1) / totalFiles) * 100);
                this.uploadProgress = globalProgress;
                this.cdr.detectChanges();
                resolve();
              }
            },
            error: reject,
          });
        });
      }

      this.statusMessage = `${totalFiles} archivo(s) subido(s) correctamente.`;
      this.selectedFiles = [];

      const input = document.getElementById('fileInput') as HTMLInputElement | null;
      if (input) {
        input.value = '';
      }

      await this.loadUploads();
      await this.loadComercios();
    } catch (error) {
      console.error(error);
      this.errorMessage = 'Ha fallado la subida de uno o más archivos.';
    } finally {
      this.uploading = false;
      setTimeout(() => {
        this.uploadProgress = null;
        this.cdr.detectChanges();
      }, 400);
      this.cdr.detectChanges();
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
    this.currentUploadsPage = 1;
  }

  async loadComercios(): Promise<void> {
    this.loadingComercios = true;

    try {
      this.comercios = await firstValueFrom(this.uploadService.listComercios());
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo cargar el listado de comercios.';
    } finally {
      this.loadingComercios = false;
    }
  }

  async processZelenza(uploadId: number): Promise<void> {
    this.processingIds.add(uploadId);
    this.statusMessage = '';
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      this.selectedProcessResult = await firstValueFrom(this.uploadService.processZelenza(uploadId));
      this.statusMessage = `Procesamiento Zelenza completado para la imagen ${uploadId}.`;
      await this.reloadAll();
      await this.loadUploadDetail(uploadId);

      if (this.selectedProcessResult?.estado_comercio?.row?.id) {
        await this.loadComercioDetail(this.selectedProcessResult.estado_comercio.row.id);
        this.manualChoice = null;
      }
    } catch (error) {
      console.error(error);
      this.errorMessage = `No se pudo procesar la plantilla Zelenza de la imagen ${uploadId}.`;
    } finally {
      this.processingIds.delete(uploadId);
      this.cdr.detectChanges();
    }
  }

  async loadUploadDetail(uploadId: number): Promise<void> {
    this.loadingUploadDetailId = uploadId;
    this.errorMessage = '';

    try {
      this.selectedUploadDetail = await firstValueFrom(this.uploadService.getUploadZelenza(uploadId));
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo cargar el detalle de la extracción.';
    } finally {
      this.loadingUploadDetailId = null;
    }
  }

  async loadComercioDetail(comercioId: number): Promise<void> {
    this.loadingComercioDetailId = comercioId;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      this.selectedComercio = await firstValueFrom(this.uploadService.getComercio(comercioId));
      this.manualInitialData = this.mapSelectedComercioToManualInitialData(this.selectedComercio);
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo cargar la ficha del comercio.';
    } finally {
      this.loadingComercioDetailId = null;
      this.cdr.detectChanges();
    }
  }

  setManualChoice(value: boolean): void {
    this.manualChoice = value;

    if (value && this.selectedComercio) {
      this.manualInitialData = this.mapSelectedComercioToManualInitialData(this.selectedComercio);
    }

    this.cdr.detectChanges();
  }

  async saveManualFields(payload: ManualCommercePayload): Promise<void> {
    if (!this.selectedComercio?.id) return;

    this.savingManual = true;
    this.errorMessage = '';
    this.statusMessage = '';
    this.cdr.detectChanges();

    try {
      this.selectedComercio = await firstValueFrom(
        this.uploadService.updateManual(this.selectedComercio.id, payload)
      );

      this.manualInitialData = this.mapSelectedComercioToManualInitialData(this.selectedComercio);
      this.statusMessage = 'Campos manuales guardados correctamente.';
      await this.loadComercios();
      this.manualChoice = false;
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudieron guardar los campos manuales.';
    } finally {
      this.savingManual = false;
      this.cdr.detectChanges();
    }
  }

  mapSelectedComercioToManualInitialData(comercio: ZelenzaCommerceDetail): ManualCommerceInitialData {
    return {
      ns_inst_manual: comercio.ns_inst_actual,
      sector: comercio.sector,
      tipo: comercio.tipo,
      comentario: comercio.comentario,
      actuacion: comercio.actuacion,
      coordenada_lat: comercio.coordenada_lat,
      coordenada_lng: comercio.coordenada_lng,
      contactos: comercio.contactos_manuales?.map((c) => ({
        nombre: c.nombre,
        orden: c.orden,
      })) ?? [],
    };
  }

  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    const value = bytes / Math.pow(1024, index);

    return `${value.toFixed(2)} ${units[index]}`;
  }

}