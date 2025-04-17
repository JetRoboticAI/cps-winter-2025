// Prepare the static route and stop data
package bus_info

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strconv"
)

var RouteIdToName map[string]string
var StopIdToName map[string]string

func init() {
	fmt.Println("Start Initing")
	RouteIdToName = getRoutes()
	StopIdToName = getStops()
}

// GetRoutes parses the static routes file and returns a id-to-name map
func getRoutes() map[string]string {
	file, err := os.Open("bus_info/routes.csv")

	if err != nil {
		log.Fatal("Enable to open route file")
	}
	defer file.Close()

	reader := csv.NewReader(file)

	line, err := reader.Read()
	if err != nil {
		log.Fatal(err)
	}

	headers := make(map[string]int, len(line))
	for i, h := range line {
		if h == "" {
			h = "NULL" + strconv.Itoa(i)
		}
		headers[h] = i
	}

	res := make(map[string]string, 100)

	idx1 := headers["route_id"]
	idx2 := headers["route_short_name"]

	for {
		line, err = reader.Read()
		if err != nil {
			break
		}

		route_short_name := line[idx2]
		route_id := line[idx1]

		res[route_id] = route_short_name
	}

	return res

}

func getStops() map[string]string {
	file, err := os.Open("bus_info/stops.csv")
	if err != nil {
		log.Fatal("Unable to open stops file: ", err)
	}

	reader := csv.NewReader(file)

	line, err := reader.Read()
	if err != nil {
		log.Fatal(err)
	}

	headers := make(map[string]int, len(line))
	for i, h := range line {
		if h == "" {
			h = "NULL" + strconv.Itoa(i)
		}
		headers[h] = i
	}

	idx1 := headers["stop_id"]
	idx2 := headers["stop_name"]

	res := make(map[string]string, 1000)

	for {
		line, err = reader.Read()
		if err != nil {
			break
		}

		stop_id := line[idx1]
		stop_name := line[idx2]

		res[stop_id] = stop_name
	}
	return res
}
