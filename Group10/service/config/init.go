package config

import (
	"encoding/json"
	"log"
	"os"
)

type HivemqConfig struct {
	URL      string `json:"url"`
	Port     int    `json:"port"`
	ClientId string `json:"client_id"`
	Username string `json:"username"`
	Password string `json:"password"`
}

type ServerConfig struct {
	Port int `json:"port"`
}

type SubscribeConfig struct {
	Topic   string `json:"topic"`
	Qos     int    `json:"qos"`
	RouteId string `json:"route_id"`
	StopId  string `json:"stop_id"`
}

type Config struct {
	Hivemq     HivemqConfig      `json:"hivemq"`
	Server     ServerConfig      `json:"server"`
	Subscribes []SubscribeConfig `json:"subscribes"`
}

var DeployConfig Config

func init() {
	log.Println("Initing config")
	DeployConfig = Config{}
	configFile, err := os.Open("./config/config.json")
	if err != nil {
		panic("Unable to open config file: " + err.Error())
	}
	defer configFile.Close()

	err = json.NewDecoder(configFile).Decode(&DeployConfig)
	if err != nil {
		panic("Unable to decode config file: " + err.Error())
	}
	log.Printf("Config loaded successfully: %+v\n", DeployConfig)
}
