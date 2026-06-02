import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class WebsocketService {
  private socket$: WebSocketSubject<unknown> = webSocket('ws://localhost:8000/ws/dashboard');

  events$(): Observable<unknown> {
    return this.socket$.asObservable();
  }

  send(message: unknown): void {
    this.socket$.next(message);
  }
}
