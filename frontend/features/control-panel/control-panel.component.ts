import { Component } from '@angular/core';
import { WebsocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-control-panel',
  template: `
    <button (click)="pause()">Pause</button>
    <button (click)="resume()">Resume</button>
  `
})
export class ControlPanelComponent {
  constructor(private ws: WebsocketService) {}

  pause(): void {
    this.ws.send({ command: 'PAUSE' });
  }

  resume(): void {
    this.ws.send({ command: 'RESUME' });
  }
}
