package main

import (
	"fmt"
	"service/bus_info"
	"service/config"
)

func main() {
	bus_info.ShowAll()
	bus_info.FetchRawTripUpdates()

	// Get subscriptions from config
	subs := make([]bus_info.Subscription, 0)
	for _, sub := range config.DeployConfig.Subscribes {
		subs = append(subs, bus_info.Subscription{
			Topic:   sub.Topic,
			RouteID: sub.RouteId,
			StopID:  sub.StopId,
		})
	}

	m := bus_info.GetAll()
	notifications, err := bus_info.GetNotificationsV2(subs, m)
	if err != nil {
		fmt.Println("Error getting notifications:", err)
		return
	}

	for topic, notification := range notifications {
		if notification.IsValid {
			fmt.Printf("\n--- Notification for %s ---\n", topic)
			// fmt.Printf("Trip ID: %s\n", notification.TripID)
			fmt.Printf("Route Number: %s\n", notification.RouteNumber)
			fmt.Printf("Stop Name: %s\n", notification.StopName)
			fmt.Printf("Next Arrival Time: %d seconds\n", notification.NextArrivalTime)
		} else {
			fmt.Printf("\nNo valid notification for %s\n", topic)
		}
	}
}
