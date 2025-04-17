package main

import (
	"encoding/json"
	"log"
	"time"

	"service/bus_info"
	"service/config"
	"service/mqtt_part"
)

func publishNotification(topic string, notification bus_info.Notification) {
	raw, err := json.Marshal(notification)
	if err != nil {
		log.Fatal(err)
	}

	err = mqtt_part.Publish(topic, raw, 3)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("Published to %s: %+v\n", topic, notification)
}

func start() {
	log.Println("Starting the service...")

	// Get subscriptions from config
	subs := make([]bus_info.Subscription, 0)
	for _, sub := range config.DeployConfig.Subscribes {
		subs = append(subs, bus_info.Subscription{
			Topic:   sub.Topic,
			RouteID: sub.RouteId,
			StopID:  sub.StopId,
		})
	}

	for {
		func() {
			defer time.Sleep(5 * time.Second) // Sleep for 5 seconds before the next iteration
			// Fetch the raw trip updates
			bus_info.FetchRawTripUpdates()

			// Get notifications for all subscribed routes/stops
			m := bus_info.GetAll()
			notifications, err := bus_info.GetNotificationsV2(subs, m)
			if err != nil {
				log.Println("Error getting notifications:", err)
				return
			}

			// Publish each notification to its topic
			for topic, notification := range notifications {
				if notification.IsValid {
					log.Printf("Next arrival at %s for route %s at stop %s",
						time.Unix(notification.NextArrivalTime, 0).Format("3:04 PM"),
						notification.RouteNumber,
						notification.StopName)

					go publishNotification(topic, notification)
				}
			}
		}()
	}
}

func main() {
	// TODO: graceful shutdown
	defer mqtt_part.Cleanup()
	start()
}
