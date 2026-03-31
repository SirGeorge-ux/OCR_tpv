import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface ManualCommerceContactInput {
  nombre: string;
  orden: number;
}

export interface ManualCommercePayload {
  ns_inst_manual: string | null;
  sector: string | null;
  tipo: string | null;
  comentario: string | null;
  actuacion: number;
  coordenada_lat: number | null;
  coordenada_lng: number | null;
  geocoded_at: string | null;
  contactos: ManualCommerceContactInput[];
}

export interface ManualCommerceInitialData {
  ns_inst_manual?: string | null;
  sector?: string | null;
  tipo?: string | null;
  comentario?: string | null;
  actuacion?: number | null;
  coordenada_lat?: number | null;
  coordenada_lng?: number | null;
  contactos?: Array<{
    nombre: string;
    orden?: number;
  }>;
}

interface ManualContactDraft {
  nombre: string;
}

@Component({
  selector: 'app-manual-commerce-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './manual-commerce-form.component.html',
  styleUrl: './manual-commerce-form.component.css'
})
export class ManualCommerceFormComponent implements OnChanges {
  @Input() title = 'Campos manuales opcionales';
  @Input() submitText = 'Guardar';
  @Input() savingText = 'Guardando...';
  @Input() saving = false;
  @Input() showTerminalField = true;
  @Input() initialData: ManualCommerceInitialData | null = null;

  @Output() save = new EventEmitter<ManualCommercePayload>();

  form = {
    ns_inst_manual: '',
    sector: '',
    tipo: '',
    comentario: '',
    actuacion: 0,
    coordenada_lat: null as number | null,
    coordenada_lng: null as number | null,
  };

  contactsCount = 0;
  contacts: ManualContactDraft[] = [];

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['initialData']) {
      this.loadInitialData();
    }
  }

  trackByIndex(index: number): number {
    return index;
  }

  syncContacts(): void {
    if (this.contactsCount < this.contacts.length) {
      this.contacts = this.contacts.slice(0, this.contactsCount);
      return;
    }

    while (this.contacts.length < this.contactsCount) {
      this.contacts.push({ nombre: '' });
    }
  }

  submitForm(): void {
    const hasCoordinates =
      this.form.coordenada_lat !== null &&
      this.form.coordenada_lng !== null;

    const payload: ManualCommercePayload = {
      ns_inst_manual: this.normalizeString(this.form.ns_inst_manual),
      sector: this.normalizeString(this.form.sector),
      tipo: this.normalizeString(this.form.tipo),
      comentario: this.normalizeString(this.form.comentario),
      actuacion: Number(this.form.actuacion || 0),
      coordenada_lat: this.form.coordenada_lat,
      coordenada_lng: this.form.coordenada_lng,
      geocoded_at: hasCoordinates ? new Date().toISOString() : null,
      contactos: this.contacts
        .map((contact, index) => ({
          nombre: contact.nombre.trim(),
          orden: index + 1,
        }))
        .filter((item) => item.nombre.length > 0),
    };

    this.save.emit(payload);
  }

  private loadInitialData(): void {
    const data = this.initialData;

    this.form = {
      ns_inst_manual: data?.ns_inst_manual ?? '',
      sector: data?.sector ?? '',
      tipo: data?.tipo ?? '',
      comentario: data?.comentario ?? '',
      actuacion: Number(data?.actuacion ?? 0),
      coordenada_lat: data?.coordenada_lat ?? null,
      coordenada_lng: data?.coordenada_lng ?? null,
    };

    const initialContacts = data?.contactos ?? [];
    this.contacts = initialContacts
      .sort((a, b) => (a.orden ?? 0) - (b.orden ?? 0))
      .map((item) => ({
        nombre: item.nombre ?? '',
      }));

    this.contactsCount = this.contacts.length;
  }

  private normalizeString(value: string | null | undefined): string | null {
    const text = (value ?? '').trim();
    return text.length ? text : null;
  }
}