// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package domain

import "time"

type Criterion struct {
	Name        string  `json:"name"`
	Weight      float64 `json:"weight"`
	Description string  `json:"description"`
	MaxScore    float64 `json:"max_score"`
}

type Hackathon struct {
	ID            string      `json:"id"`
	Title         string      `json:"title"`
	Date          time.Time   `json:"date"`
	Description   string      `json:"description"`
	Goal          string      `json:"goal"`
	Status        string      `json:"status"`
	Criteria      []Criterion `json:"criteria"`
	BonusCriteria []Criterion `json:"bonus_criteria"`
}

type HackathonRepository interface {
	GetAll() ([]Hackathon, error)
	GetByID(id string) (Hackathon, error)
	Create(hackathon Hackathon) error
	Delete(id string) error
}
