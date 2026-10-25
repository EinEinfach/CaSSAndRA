package mqttapi

import (
	"context"
	"fmt"

	"github.com/EinEinfach/CaSSAndRA/next/backend/settings"
	"github.com/EinEinfach/CaSSAndRA/next/backend/system"
)

// Notifier sends a message to the user (Telegram, Pushover).
type Notifier interface {
	Send(ctx context.Context, text string) error
}

// System reports the load of the computer.
type System interface {
	Read() system.Info
}

func (a *API) serverJSON() ServerJSON {
	out := ServerJSON{Software: "CaSSAndRA", Version: a.cfg.Version}
	if a.system == nil {
		return out
	}
	info := a.system.Read()
	round := func(v *float64) *Float {
		if v == nil {
			return nil
		}
		f := round2(*v)
		return &f
	}
	out.CPULoad, out.CPUTemp = round(info.CPULoadPercent), round(info.CPUTempC)
	out.MemUsage, out.HDDUsage = round(info.MemUsedPercent), round(info.DiskUsedPercent)
	return out
}

// serverCommand restarts CaSSAndRA or shuts the computer down, like legacy:
// with a robot on the serial port (sitting on the same computer) the robot
// is shut down first.
func (a *API) serverCommand(ctx context.Context, c command) error {
	switch c.Command {
	case "restart":
		if a.cfg.Restart == nil {
			return fmt.Errorf("%w: restart is not available", ErrUnknown)
		}
		a.log.Info("mqtt api: restart")
		a.cfg.Restart()
		return nil
	case "shutdown":
		if a.cfg.PowerOff == nil {
			return fmt.Errorf("%w: shutdown is not available", ErrUnknown)
		}
		if a.settings != nil && a.settings.Get().Connection.Kind == settings.LinkUART {
			if err := a.robot.Shutdown(ctx); err != nil {
				a.log.Warn("mqtt api: robot shutdown before the computer's", "err", err)
			}
		}
		a.log.Warn("mqtt api: shutting the computer down")
		return a.cfg.PowerOff(ctx)
	case "sendMessage":
		v, err := c.strings()
		if err != nil || len(v) == 0 {
			return fmt.Errorf("%w: server sendMessage wants [\"text\"]", ErrInvalid)
		}
		if a.notifier == nil {
			return fmt.Errorf("%w: no message service", ErrUnknown)
		}
		return a.notifier.Send(ctx, v[0])
	}
	return fmt.Errorf("%w: server command %q", ErrUnknown, c.Command)
}
