import { Component } from '@angular/core';
import { Observable } from 'rxjs';
import { WebsocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-live-feed',
  template: '<pre>{{ events$ | async | json }}</pre>'
})
export class LiveFeedComponent {
  events$: Observable<unknown>;

  constructor(ws: WebsocketService) {
    this.events$ = ws.events$();
  }
}
