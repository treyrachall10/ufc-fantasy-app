package types

import (
	"cloud.google.com/go/pubsub/v2"
)

type ImageJob struct {
	ID             int64           `json:"id"`
	Msg            *pubsub.Message `json:"-"`
	ImgURL         string          `json:"img_url"`
	FighterID      int64           `json:"fighter_id"`
	NormalizedName string          `json:"normalized_name"`
	RetryCount     int             `json:"retry_count"`
	SupabasePath   string          `json:"-"`
}
