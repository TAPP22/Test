
L'editor compatto include quattro nuovi blocchi, disponibili nella palette sopra ai pennelli classici e con i tasti indicati:

- `C` Cassa: ostacolo solido con texture di legno; non puoi attraversarla.
- `P` Runa ambra e `Q` runa azzurra: piastre sul pavimento. Guardale da vicino e premi `E` per attivarle.
- `L` Blocco sigillato: parete solida con texture runica. Si apre quando la mappa contiene almeno una runa `P` e una `Q` e tutte le rune sono state attivate.

Per costruire un enigma, dipingi le rune e il blocco `L` sulle celle della griglia, quindi salva la mappa. Le rune non bloccano il movimento; casse e blocchi sigillati sì. Le mappe create prima di questa aggiunta continuano a caricarsi normalmente.

Le texture della cassa e del blocco sigillato sono generate proceduralmente e seguono l'illuminazione del renderer.

## Piani, blocchi 3D e trigger

Nella palette dell'editor, `U` e `V` sono scale collegate: per salire, metti `U` su un piano e `V` nella stessa cella del piano successivo; per scendere, la coppia funziona al contrario. Il passaggio avviene camminando sulla scala. PgUp/PgDown restano disponibili per selezionare un piano direttamente.

`J` è una piastra che lancia automaticamente il giocatore quando ci cammina sopra. `Y` attiva un boost di velocità per 2,5 secondi. I trigger scattano quando si entra nella loro cella; `J` è disattivata nella modalità senza salto.

Per creare un blocco 3D personalizzato, seleziona `B` nella palette e cambia le misure prima di piazzarlo: `,` / `.` regolano la larghezza, `M` / `N` la profondità e `[` / `]` l'altezza. L'hitbox coincide con le dimensioni mostrate. I blocchi bassi sono calpestabili; quelli sopra l'altezza di passo sono ostacoli solidi. I blocchi e le scale vengono salvati nei dati dei rispettivi piani.

## Piani, blocchi 3D e trigger

Nella palette dell'editor, `U` e `V` sono scale collegate: per salire, metti `U` su un piano e `V` nella stessa cella del piano successivo; per scendere, la coppia funziona al contrario. Il passaggio avviene camminando sulla scala. PgUp/PgDown restano disponibili per selezionare un piano direttamente.

`J` è una piastra che lancia automaticamente il giocatore quando ci cammina sopra. `Y` attiva un boost di velocità temporaneo. I trigger scattano quando si entra nella loro cella.

Per creare un blocco 3D personalizzato, seleziona `B Blocco 3D` e cambia le misure prima di piazzarlo: `,` / `.` regolano la larghezza, `M` / `N` la profondità e `[` / `]` l'altezza. L'hitbox coincide con le dimensioni mostrate. I blocchi bassi sono calpestabili; quelli sopra l'altezza di passo sono ostacoli solidi. I blocchi e le scale vengono salvati nei dati dei rispettivi piani.