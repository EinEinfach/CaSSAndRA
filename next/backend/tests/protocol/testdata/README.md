# Protokoll-Testdaten

Jede `.txt`-Datei enthält genau eine Antwortzeile, so wie der Roboter sie sendet
(Payload, `,0x` + Prüfsumme, `\r\n`). `.gitattributes` verhindert, dass Git die
Zeilenenden ändert.

**Herkunft:** Synthetisch, aber exakt nach dem Format der Sunray-Firmware
(`sunray/comm.cpp`, `Comm::cmdAnswer`, `cmdSummary`, `cmdStats`, `cmdVersion`,
`cmdObstacles`, Stand Sunray 1.0.332). Die Prüfsummen wurden unabhängig vom
Go-Code mit Python berechnet. Ältere Firmware-Varianten (`*_fw_*`) bilden die
kürzeren Antworten nach, die der Legacy-Code in `sunraycommstack.py` auffüllt.

**Echte Mitschnitte ergänzen:** Zeile aus einem Debug-Log (`RX:`) als neue Datei
ablegen, z. B. `state_real_2026_10_alfred.txt`, und in `replies_test.go` einen
Testfall mit den erwarteten Werten hinzufügen.

`fuzz/` enthält Eingaben, mit denen der Fuzzer Abstürze gefunden hat. Sie laufen
bei jedem `go test` als Regressionstests mit.
