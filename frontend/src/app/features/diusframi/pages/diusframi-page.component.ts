import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-diusframi-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="shell">
      <div class="topbar">
        <a routerLink="/" class="back-link">← Volver al inicio</a>
      </div>

      <header class="header">
        <h1>OCR TPV - Diusframi</h1>
        <p>Esta funcionalidad estará disponible en la próxima fase.</p>
      </header>

      <section class="card">
        <p>Próximamente...</p>
      </section>
    </main>
  `,
  styles: [`
    .shell {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 16px;
      font-family: Arial, Helvetica, sans-serif;
    }

    .topbar {
      margin-bottom: 16px;
    }

    .back-link {
      text-decoration: none;
      font-weight: 600;
      color: #374151;
    }

    .header {
      margin-bottom: 24px;
    }

    .card {
      border: 1px solid #ddd;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      background: #fff;
    }
  `]
})
export class DiusframiPageComponent {}
