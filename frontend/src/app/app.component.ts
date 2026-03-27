import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UploadComponent } from './upload/upload.component';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, UploadComponent],
    template: `
    <main class="shell">
      <header class="header">
        <h1>OCR TPV - Fase 1</h1>
        <p>Subida de capturas y registro en SQLite</p>
      </header>

      <app-upload></app-upload>
    </main>
  `,
    styles: [`
    .shell {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 16px;
      font-family: Arial, Helvetica, sans-serif;
    }

    .header {
      margin-bottom: 24px;
    }

    h1 {
      margin: 0 0 8px;
    }

    p {
      margin: 0;
      color: #555;
    }
  `]
})
export class AppComponent { }