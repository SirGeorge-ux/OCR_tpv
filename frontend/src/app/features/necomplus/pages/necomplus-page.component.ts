import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import {
  NecomplusCommerceDetail,
  NecomplusCommerceSummary,
  NecomplusProcessResponse,
  NecomplusService,
  UploadRecord,
} from '../services/necomplus.service';
import {
  ManualCommerceFormComponent,
  ManualCommerceInitialData,
  ManualCommercePayload,
} from '../../../shared/components/manual-commerce-form/manual-commerce-form.component';

@Component({
  selector: 'app-necomplus-page',
  standalone: true,
  imports: [CommonModule, RouterLink, ManualCommerceFormComponent],
  templateUrl: './necomplus-page.component.html',
  styleUrl: './necomplus-page.component.css'
})

export class NecomplusPageComponent implements OnInit {
  selectedComercioFile: File | null = null;
  selectedDetalleFile: File | null = null;

  uploadedComercio: UploadRecord | null = null;
  uploadedDetalle: UploadRecord | null = null;

  uploadProgressComercio: number | null = null;
  uploadProgressDetalle: number | null = null;

  processResult: NecomplusProcessResponse | null = null;
  comercios: NecomplusCommerceSummary[] = [];
  selectedComercio: NecomplusCommerceDetail | null = null;
  selectedComercioId: number | null = null;

  uploadingComercio = false;
  uploadingDetalle = false;
  processingPair = false;
  loadingComercios = false;
  savingManual = false;

  manualChoice: boolean | null = null;
  manualContactsCount = 0;
  manualContacts: string[] = [];
  manualInitialData: ManualCommerceInitialData | null = null;

  manualForm = {
    ns_inst_manual: '',
    sector: '',
    tipo: '',
    comentario: '',
    actuacion: 0,
    coordenada_lat: null as number | null,
    coordenada_lng: null as number | null,
  };

  statusMessage = '';
  errorMessage = '';

  constructor(
    private readonly necomplusService: NecomplusService,
    private readonly cdr: ChangeDetectorRef,
  ) { }

  async ngOnInit(): Promise<void> {
    await this.loadComercios();
  }

  onComercioFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedComercioFile = input.files?.[0] ?? null;
    this.cdr.detectChanges();
  }

  onDetalleFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedDetalleFile = input.files?.[0] ?? null;
    this.cdr.detectChanges();
  }

  uploadComercio(): void {
    if (!this.selectedComercioFile || this.uploadingComercio) return;

    const file = this.selectedComercioFile;

    this.uploadingComercio = true;
    this.uploadProgressComercio = 0;
    this.errorMessage = '';
    this.statusMessage = '';
    this.cdr.detectChanges();

    this.necomplusService.uploadWithProgress(file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          const total = event.total ?? file.size ?? 1;
          this.uploadProgressComercio = Math.round((event.loaded * 100) / total);
          this.cdr.detectChanges();
        }

        if (event.type === HttpEventType.Response && event.body) {
          this.uploadedComercio = event.body;
          this.selectedComercioFile = null;
          this.uploadingComercio = false;
          this.uploadProgressComercio = 100;
          this.statusMessage = `Captura de comercio subida correctamente. ID: ${event.body.id}`;
          this.resetFileInput('comercioInput');
          this.cdr.detectChanges();

          setTimeout(() => {
            this.uploadProgressComercio = null;
            this.cdr.detectChanges();
          }, 400);
        }
      },
      error: (error) => {
        console.error(error);
        this.errorMessage = 'No se pudo subir la captura de comercio.';
        this.uploadingComercio = false;
        this.uploadProgressComercio = null;
        this.cdr.detectChanges();
      }
    });
  }

  uploadDetalle(): void {
    if (!this.selectedDetalleFile || this.uploadingDetalle) return;

    const file = this.selectedDetalleFile;

    this.uploadingDetalle = true;
    this.uploadProgressDetalle = 0;
    this.errorMessage = '';
    this.statusMessage = '';
    this.cdr.detectChanges();

    this.necomplusService.uploadWithProgress(file).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          const total = event.total ?? file.size ?? 1;
          this.uploadProgressDetalle = Math.round((event.loaded * 100) / total);
          this.cdr.detectChanges();
        }

        if (event.type === HttpEventType.Response && event.body) {
          this.uploadedDetalle = event.body;
          this.selectedDetalleFile = null;
          this.uploadingDetalle = false;
          this.uploadProgressDetalle = 100;
          this.statusMessage = `Captura de detalle subida correctamente. ID: ${event.body.id}`;
          this.resetFileInput('detalleInput');
          this.cdr.detectChanges();

          setTimeout(() => {
            this.uploadProgressDetalle = null;
            this.cdr.detectChanges();
          }, 400);
        }
      },
      error: (error) => {
        console.error(error);
        this.errorMessage = 'No se pudo subir la captura de detalle.';
        this.uploadingDetalle = false;
        this.uploadProgressDetalle = null;
        this.cdr.detectChanges();
      }
    });
  }

  async processPair(): Promise<void> {
    if (!this.uploadedComercio || !this.uploadedDetalle) {
      this.errorMessage = 'Debes subir las dos capturas antes de procesar.';
      return;
    }

    this.processingPair = true;
    this.errorMessage = '';
    this.statusMessage = 'Procesando pareja Necomplus...';
    this.cdr.detectChanges();

    try {
      this.processResult = await firstValueFrom(
        this.necomplusService.processPair(this.uploadedComercio.id, this.uploadedDetalle.id)
      );

      this.selectedComercioId = this.processResult.estado_comercio.row.id;
      this.manualChoice = null;

      await this.loadComercios();
      await this.loadComercioDetail(this.selectedComercioId);

      this.clearUploadedPair();
      this.statusMessage = 'Pareja Necomplus procesada correctamente.';
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo procesar la pareja Necomplus.';
    } finally {
      this.processingPair = false;
      this.cdr.detectChanges();
    }
  }

  async loadComercios(): Promise<void> {
    this.loadingComercios = true;
    this.cdr.detectChanges();

    try {
      this.comercios = await firstValueFrom(this.necomplusService.listComercios());
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo cargar el listado de comercios Necomplus.';
    } finally {
      this.loadingComercios = false;
      this.cdr.detectChanges();
    }
  }

  async loadComercioDetail(comercioId: number): Promise<void> {
    try {
      this.selectedComercio = await firstValueFrom(this.necomplusService.getComercio(comercioId));
      this.selectedComercioId = comercioId;
      this.manualInitialData = this.mapSelectedComercioToManualInitialData(this.selectedComercio);
      this.cdr.detectChanges();
    } catch (error) {
      console.error(error);
      this.errorMessage = 'No se pudo cargar la ficha del comercio Necomplus.';
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
    if (!this.selectedComercioId) return;

    this.savingManual = true;
    this.errorMessage = '';
    this.statusMessage = '';
    this.cdr.detectChanges();

    try {
      this.selectedComercio = await firstValueFrom(
        this.necomplusService.updateManual(this.selectedComercioId, payload)
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

  mapSelectedComercioToManualInitialData(comercio: NecomplusCommerceDetail) {
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

  private clearUploadedPair(): void {
    this.selectedComercioFile = null;
    this.selectedDetalleFile = null;

    this.uploadedComercio = null;
    this.uploadedDetalle = null;

    this.uploadProgressComercio = null;
    this.uploadProgressDetalle = null;

    this.resetFileInput('comercioInput');
    this.resetFileInput('detalleInput');
  }
  private resetFileInput(inputId: string): void {
    const input = document.getElementById(inputId) as HTMLInputElement | null;
    if (input) {
      input.value = '';
    }
  }
}