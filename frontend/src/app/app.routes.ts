import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home.component';
import { ZelenzaPageComponent } from './features/zelenza/pages/zelenza-page.component';
import { NecomplusPageComponent } from './features/necomplus/pages/necomplus-page.component';
import { DiusframiPageComponent } from './features/diusframi/pages/diusframi-page.component';

export const routes: Routes = [
    { path: '', component: HomeComponent },
    { path: 'plantillas/zelenza', component: ZelenzaPageComponent },
    { path: 'plantillas/necomplus', component: NecomplusPageComponent },
    { path: 'plantillas/diusframi', component: DiusframiPageComponent },
    { path: '**', redirectTo: '' }
];