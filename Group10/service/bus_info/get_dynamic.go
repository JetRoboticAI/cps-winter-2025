package bus_info

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"service/proto/gtfsrt"
	"time"

	"google.golang.org/protobuf/proto"
)

var PB_LINK string = "https://opendata.hamilton.ca/GTFS-RT/GTFS_TripUpdates.pb"

type Notification struct {
	IsValid bool `json:"is_valid"` // Indicates if there is indeed an ongoing next trip
	// TripID          string `json:"trip_id"`
	RouteNumber     string `json:"route_number"`
	StopName        string `json:"stop_name"`
	NextArrivalTime int64  `json:"next_arrival_time"`
}

func FetchRawTripUpdates() {
	// 1. First download the protobuf file
	httpClient := &http.Client{}
	req, err := http.NewRequest("GET", PB_LINK, nil)
	if err != nil {
		log.Fatalf("Unable to build request: %v", err)
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		log.Fatalf("Unable to download PB file: %v", err)
	}

	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		log.Fatalf("Fetch data not OK: %s", resp.Status)
	}

	// 2. Save it to a local file
	out, err := os.Create("test_data/GTFS_TripUpdates.pb")
	if err != nil {
		log.Fatalf("Unable to create file: %v", err)
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)

	if err != nil {
		log.Fatalf("Unable to save file: %v", err)
	}

	log.Println("Real-time trip updates fetched")
}

type Subscription struct {
	Topic   string
	RouteID string
	StopID  string
}

func GetNotifications(subscriptions []Subscription) (map[string]Notification, error) {
	results := make(map[string]Notification)

	data, err := os.ReadFile("test_data/GTFS_TripUpdates.pb")
	if err != nil {
		return nil, fmt.Errorf("unable to read file: %v", err)
	}

	feed := &gtfsrt.FeedMessage{}
	if err := proto.Unmarshal(data, feed); err != nil {
		return nil, fmt.Errorf("unable to parse protobuf: %v", err)
	}

	// Process each subscription
	for _, sub := range subscriptions {
		res := Notification{IsValid: false}

		// Find all trips for this route/stop
		var matchingTrips []struct {
			tripID  string
			arrival int64
		}

		for _, entity := range feed.Entity {
			trip_update := entity.GetTripUpdate()
			if trip_update == nil {
				continue
			}

			trip := trip_update.GetTrip()
			if trip == nil || trip.GetRouteId() != sub.RouteID {
				continue
			}

			// Check if this trip has our stop
			for _, stop_time_update := range trip_update.GetStopTimeUpdate() {
				if stop_time_update.GetStopId() == sub.StopID {
					arrival := stop_time_update.GetArrival()
					if arrival != nil {
						matchingTrips = append(matchingTrips, struct {
							tripID  string
							arrival int64
						}{
							tripID:  trip.GetTripId(),
							arrival: arrival.GetTime(),
						})
					}
					break // Found the stop in this trip
				}
			}
		}

		if len(matchingTrips) > 0 {
			// Find earliest arrival time
			var earliestTrip struct {
				tripID  string
				arrival int64
			}
			for _, trip := range matchingTrips {
				if earliestTrip.tripID == "" || trip.arrival < earliestTrip.arrival {
					earliestTrip = trip
				}
			}

			next_arrival_time := earliestTrip.arrival - time.Now().Unix()
			if next_arrival_time >= 0 {
				res = Notification{
					IsValid: true,
					// TripID:          earliestTrip.tripID,
					RouteNumber:     RouteIdToName[sub.RouteID],
					StopName:        StopIdToName[sub.StopID],
					NextArrivalTime: next_arrival_time,
				}
			}
		}

		results[sub.Topic] = res
	}

	return results, nil
}

func GetNotificationsV2(subscriptions []Subscription, m map[string]int64) (map[string]Notification, error) {
	results := make(map[string]Notification)

	// Process each subscription
	for _, sub := range subscriptions {
		res := Notification{IsValid: false}

		// Find all trips for this route/stop
		key := sub.RouteID + sub.StopID
		if arrival, ok := m[key]; ok {
			next_arrival_time := arrival - time.Now().Unix()
			if next_arrival_time >= 0 {
				res = Notification{
					IsValid:         true,
					RouteNumber:     RouteIdToName[sub.RouteID],
					StopName:        StopIdToName[sub.StopID],
					NextArrivalTime: next_arrival_time,
				}
			}
		}

		results[sub.Topic] = res
	}

	return results, nil
}

func ShowAll() {
	// Display all the next arrival times for all the stops and routes
	rtData, err := os.ReadFile("test_data/GTFS_TripUpdates.pb")
	if err != nil {
		log.Fatalf("Unable to read file: %v", err)
	}

	feed := &gtfsrt.FeedMessage{}
	if err := proto.Unmarshal(rtData, feed); err != nil {
		log.Fatalf("Unable to parse protobuf: %v", err)
	}

	for _, entity := range feed.Entity {
		trip_update := entity.GetTripUpdate()
		if trip_update == nil {
			continue
		}
		trip := trip_update.GetTrip()
		if trip == nil {
			continue
		}
		stop_time_updates := trip_update.GetStopTimeUpdate()
		for _, stop_time_update := range stop_time_updates {
			stop_id := stop_time_update.GetStopId()
			arrival := stop_time_update.GetArrival()
			if arrival == nil {
				continue
			}
			fmt.Printf("Route %s, Stop %s, Arrival %d\n",
				trip.GetRouteId(), stop_id, arrival.GetTime())
		}
	}

}

func GetAll() map[string]int64 {
	res := make(map[string]int64)
	// Display all the next arrival times for all the stops and routes
	rtData, err := os.ReadFile("test_data/GTFS_TripUpdates.pb")
	if err != nil {
		log.Fatalf("Unable to read file: %v", err)
	}

	feed := &gtfsrt.FeedMessage{}
	if err := proto.Unmarshal(rtData, feed); err != nil {
		log.Fatalf("Unable to parse protobuf: %v", err)
	}

	for _, entity := range feed.Entity {
		trip_update := entity.GetTripUpdate()
		if trip_update == nil {
			continue
		}
		trip := trip_update.GetTrip()
		if trip == nil {
			continue
		}
		stop_time_updates := trip_update.GetStopTimeUpdate()
		for _, stop_time_update := range stop_time_updates {
			stop_id := stop_time_update.GetStopId()
			arrival := stop_time_update.GetArrival()
			if arrival == nil {
				continue
			}
			// fmt.Printf("Route %s, Stop %s, Arrival %d\n",
			// 	trip.GetRouteId(), stop_id, arrival.GetTime())
			key := trip.GetRouteId() + stop_id
			if cur, ok := res[key]; ok {
				if cur > arrival.GetTime() {
					res[key] = arrival.GetTime()
				}
			} else {
				res[key] = arrival.GetTime()
			}
		}
	}
	return res

}
