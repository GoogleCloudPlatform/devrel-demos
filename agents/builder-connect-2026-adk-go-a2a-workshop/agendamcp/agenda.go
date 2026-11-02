// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"html"
	"io"
	"net/http"
	"regexp"
	"sort"
	"strings"
	"time"
	_ "time/tzdata" // Europe/Warsaw must resolve in distroless containers too.
)

// eventURLs are the event site's public agenda API for the two days.
var eventURLs = []string{
	"https://cloudonair.withgoogle.com/api/events/summit-builder-connect-poland-2026",
	"https://cloudonair.withgoogle.com/api/events/google-cloud-summit-poland-2026",
}

// fetchEvents downloads both agendas from the event site, so the server
// serves the current agenda and the repository keeps no copy of it.
func fetchEvents(ctx context.Context) ([][]byte, error) {
	client := &http.Client{Timeout: 30 * time.Second}
	var bodies [][]byte
	for _, u := range eventURLs {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Accept", "application/json")
		resp, err := client.Do(req)
		if err != nil {
			return nil, fmt.Errorf("fetch agenda: %w", err)
		}
		b, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			return nil, fmt.Errorf("fetch agenda %s: %w", u, err)
		}
		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("fetch agenda %s: %s", u, resp.Status)
		}
		bodies = append(bodies, b)
	}
	return bodies, nil
}

var warsaw = mustLoad("Europe/Warsaw")

func mustLoad(name string) *time.Location {
	loc, err := time.LoadLocation(name)
	if err != nil {
		panic(err)
	}
	return loc
}

// Session is one agenda entry, cleaned up for a model to read.
type Session struct {
	ID          string   `json:"id"`
	Event       string   `json:"event"`
	Date        string   `json:"date"`  // YYYY-MM-DD, Warsaw time
	Start       string   `json:"start"` // HH:MM, Warsaw time
	End         string   `json:"end"`   // HH:MM, Warsaw time
	Title       string   `json:"title"`
	Track       string   `json:"track,omitempty"`
	Speakers    []string `json:"speakers,omitempty"`
	Description string   `json:"description,omitempty"`

	start, end time.Time
	// searchTitle and searchDesc are the title and description with
	// abbreviations spelled out, used for matching only.
	searchTitle, searchDesc string
}

// Day is one event day of the agenda.
type Day struct {
	Date  string
	Event string
}

// Agenda is an immutable, deduplicated list of sessions from one or more
// events, sorted by start time.
type Agenda struct {
	Sessions []Session
	Days     []Day
}

type rawEvent struct {
	Name  string `json:"name"`
	Talks []struct {
		ID          string `json:"id"`
		Name        string `json:"name"`
		Start       string `json:"start"`
		End         string `json:"end"`
		Description string `json:"description"`
		Speakers    []struct {
			Name    string `json:"name"`
			Company string `json:"company"`
		} `json:"speakers"`
	} `json:"talks"`
	Modules []rawModule `json:"modules"`
}

type rawModule struct {
	Type       string `json:"type"`
	Categories []struct {
		Name  string   `json:"name"`
		Talks []string `json:"talks"`
	} `json:"categories"`
	Modules []rawModule `json:"modules"`
}

var (
	lineBreaks   = regexp.MustCompile(`(?i)<br\s*/?>|</p>|</div>|</li>`)
	tags         = regexp.MustCompile(`<[^>]+>`)
	spaces       = regexp.MustCompile(`[ \t\x{00a0}]+`)
	blankLines   = regexp.MustCompile(`\n{2,}`)
	listItems    = regexp.MustCompile(`(?is)<li[^>]*>(.*?)</li>`)
	speakersHead = regexp.MustCompile(`(?i)speakers?\s*:`)
)

func toText(h string) string {
	s := lineBreaks.ReplaceAllString(h, "\n")
	s = html.UnescapeString(tags.ReplaceAllString(s, ""))
	s = spaces.ReplaceAllString(s, " ")
	lines := strings.Split(s, "\n")
	for i, l := range lines {
		lines[i] = strings.TrimSpace(l)
	}
	return strings.TrimSpace(blankLines.ReplaceAllString(strings.Join(lines, "\n"), "\n"))
}

// splitSpeakers separates the "Speakers:" part that the site appends to some
// descriptions, either as a list or as plain text, from the description.
func splitSpeakers(descHTML string) (desc string, speakers []string) {
	loc := speakersHead.FindStringIndex(descHTML)
	if loc == nil {
		return toText(descHTML), nil
	}
	tail := descHTML[loc[1]:]
	for _, m := range listItems.FindAllStringSubmatch(tail, -1) {
		if s := toText(m[1]); s != "" {
			speakers = append(speakers, s)
		}
	}
	if len(speakers) == 0 {
		for _, l := range strings.Split(toText(tail), "\n") {
			if l != "" {
				speakers = append(speakers, l)
			}
		}
	}
	return toText(descHTML[:loc[0]]), speakers
}

// mergeSpeakers appends the speakers named in the description to the
// structured ones, skipping names already listed.
func mergeSpeakers(structured, fromDesc []string) []string {
	out := structured
	for _, s := range fromDesc {
		name, _, _ := strings.Cut(s, ",")
		dup := false
		for _, have := range out {
			if h, _, _ := strings.Cut(have, ","); strings.EqualFold(strings.TrimSpace(h), strings.TrimSpace(name)) {
				dup = true
			}
		}
		if !dup {
			out = append(out, s)
		}
	}
	return out
}

// abbreviations are spelled out in the text that searches match against, so
// that a search for "agents" also finds "ADK + A2A workshop".
var abbreviations = []struct {
	re   *regexp.Regexp
	full string
}{
	{regexp.MustCompile(`\bADK\b`), "Agent Development Kit"},
	{regexp.MustCompile(`\bA2A\b`), "Agent2Agent agent-to-agent"},
	{regexp.MustCompile(`\bMCP\b`), "Model Context Protocol"},
	{regexp.MustCompile(`\bRAG\b`), "retrieval-augmented generation"},
	{regexp.MustCompile(`\bLLMs?\b`), "large language model"},
	{regexp.MustCompile(`\bGKE\b`), "Google Kubernetes Engine"},
}

func expandAbbreviations(s string) string {
	for _, a := range abbreviations {
		s = a.re.ReplaceAllStringFunc(s, func(m string) string { return m + " (" + a.full + ")" })
	}
	return s
}

// trackNames maps talk IDs to the name of the agenda track listing them.
func trackNames(mods []rawModule, into map[string]string) {
	for _, m := range mods {
		if m.Type == "AGENDA" {
			for _, c := range m.Categories {
				for _, id := range c.Talks {
					into[id] = c.Name
				}
			}
		}
		trackNames(m.Modules, into)
	}
}

func parseEvent(b []byte) ([]Session, error) {
	var ev rawEvent
	if err := json.Unmarshal(b, &ev); err != nil {
		return nil, fmt.Errorf("decode agenda: %w", err)
	}
	tracks := map[string]string{}
	trackNames(ev.Modules, tracks)
	isTrack := map[string]bool{}
	for _, name := range tracks {
		isTrack[name] = true
	}

	// The keynote, lunch and so on are listed once per track; merge them.
	byKey := map[string]int{}
	var out []Session
	for _, t := range ev.Talks {
		title := strings.TrimSpace(t.Name)
		// Entries titled after a track are "View detailed agenda" headers,
		// and one titled after the event spans the whole day. Neither is a
		// session.
		if isTrack[title] || strings.EqualFold(title, strings.TrimSpace(ev.Name)) {
			continue
		}
		start, err := time.Parse(time.RFC3339, t.Start)
		if err != nil {
			continue
		}
		end, _ := time.Parse(time.RFC3339, t.End)
		key := title + "|" + t.Start
		if i, ok := byKey[key]; ok {
			if out[i].Track != tracks[t.ID] {
				out[i].Track = "All tracks"
			}
			continue
		}
		var structured []string
		for _, s := range t.Speakers {
			structured = append(structured, strings.TrimSuffix(s.Name+", "+s.Company, ", "))
		}
		desc, fromDesc := splitSpeakers(t.Description)
		byKey[key] = len(out)
		out = append(out, Session{
			ID:          t.ID,
			Event:       strings.TrimSpace(ev.Name),
			Date:        start.In(warsaw).Format("2006-01-02"),
			Start:       start.In(warsaw).Format("15:04"),
			End:         end.In(warsaw).Format("15:04"),
			Title:       title,
			Track:       tracks[t.ID],
			Speakers:    mergeSpeakers(structured, fromDesc),
			Description: desc,
			start:       start,
			end:         end,
			searchTitle: expandAbbreviations(title),
			searchDesc:  expandAbbreviations(desc),
		})
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("agenda of %q has no sessions", ev.Name)
	}
	return out, nil
}

// loadAgenda combines the agendas of the given events.
func loadAgenda(events ...[]byte) (*Agenda, error) {
	a := &Agenda{}
	seen := map[string]bool{}
	for _, b := range events {
		sessions, err := parseEvent(b)
		if err != nil {
			return nil, err
		}
		a.Sessions = append(a.Sessions, sessions...)
		for _, s := range sessions {
			if !seen[s.Date] {
				seen[s.Date] = true
				a.Days = append(a.Days, Day{Date: s.Date, Event: s.Event})
			}
		}
	}
	sort.SliceStable(a.Sessions, func(i, j int) bool { return a.Sessions[i].start.Before(a.Sessions[j].start) })
	sort.Slice(a.Days, func(i, j int) bool { return a.Days[i].Date < a.Days[j].Date })
	return a, nil
}

// DaysText describes the agenda's days, e.g. "Builder Connect (2026-11-03)".
func (a *Agenda) DaysText() string {
	var parts []string
	for _, d := range a.Days {
		parts = append(parts, d.Event+" ("+d.Date+")")
	}
	return strings.Join(parts, " and ")
}

func (a *Agenda) hasDay(date string) bool {
	for _, d := range a.Days {
		if d.Date == date {
			return true
		}
	}
	return false
}

var stopwords = map[string]bool{
	"a": true, "an": true, "the": true, "and": true, "or": true, "of": true, "on": true, "in": true,
	"for": true, "to": true, "with": true, "about": true, "talk": true, "talks": true,
	"session": true, "sessions": true,
}

var wordRE = regexp.MustCompile(`[\p{L}\p{N}][\p{L}\p{N}+#.-]*`)

// queryPatterns turns free-text keywords into patterns. Words of four or more
// letters match anywhere, so "agents" also finds "agentic" and the Polish
// "wieloagentowe"; shorter words such as "ai" must start a word.
func queryPatterns(q string) []*regexp.Regexp {
	var out []*regexp.Regexp
	for _, w := range wordRE.FindAllString(strings.ToLower(q), -1) {
		if stopwords[w] {
			continue
		}
		if len([]rune(w)) > 3 {
			out = append(out, regexp.MustCompile(`(?i)`+regexp.QuoteMeta(strings.TrimSuffix(w, "s"))))
			continue
		}
		out = append(out, regexp.MustCompile(`(?i)\b`+regexp.QuoteMeta(w)))
	}
	return out
}

func parseClock(s string) (int, bool) {
	t, err := time.Parse("15:04", strings.TrimSpace(s))
	if err != nil {
		return 0, false
	}
	return t.Hour()*60 + t.Minute(), true
}

func minutes(hhmm string) int {
	m, _ := parseClock(hhmm)
	return m
}

// Hit is a search result and the fields the query matched in.
type Hit struct {
	Session
	MatchedIn []string
	// MatchedTerms are the terms the session mentions.
	MatchedTerms []string
	// Context is the text around the first description match, set when the
	// query matched only the description.
	Context string
}

// termPattern matches term as a whole word or phrase, case-insensitively.
func termPattern(term string) *regexp.Regexp {
	return regexp.MustCompile(`(?i)(^|[^\p{L}\p{N}_-])` + regexp.QuoteMeta(strings.TrimSpace(term)) + `($|[^\p{L}\p{N}_-])`)
}

// Search returns sessions on day (any day if empty), starting in [after,
// before), that match any of the query keywords and mention any of the terms
// (exact names or phrases); an empty query or terms matches everything. Best
// matches come first when there are more than limit, then they are ordered
// by start time.
func (a *Agenda) Search(query string, terms []string, day, after, before string, limit int) (matches []Hit, total int, err error) {
	if day != "" && !a.hasDay(day) {
		var dates []string
		for _, d := range a.Days {
			dates = append(dates, d.Date)
		}
		return nil, 0, fmt.Errorf("day must be one of %s, got %q", strings.Join(dates, ", "), day)
	}
	lo, hi := 0, 24*60
	if after != "" {
		var ok bool
		if lo, ok = parseClock(after); !ok {
			return nil, 0, fmt.Errorf("after must be HH:MM, got %q", after)
		}
	}
	if before != "" {
		var ok bool
		if hi, ok = parseClock(before); !ok {
			return nil, 0, fmt.Errorf("before must be HH:MM, got %q", before)
		}
	}
	pats := queryPatterns(query)
	var termPats []*regexp.Regexp
	var termNames []string
	for _, t := range terms {
		if strings.TrimSpace(t) != "" {
			termPats = append(termPats, termPattern(t))
			termNames = append(termNames, strings.TrimSpace(t))
		}
	}
	type scored struct {
		h     Hit
		score int
	}
	var hits []scored
	for _, s := range a.Sessions {
		if day != "" && s.Date != day {
			continue
		}
		if m := minutes(s.Start); m < lo || m >= hi {
			continue
		}
		score := 0
		in := map[string]bool{}
		ctx := ""
		for _, p := range pats {
			switch {
			case p.MatchString(s.searchTitle):
				score += 3
				in["title"] = true
			case p.MatchString(strings.Join(s.Speakers, " ")):
				score += 2
				in["speakers"] = true
			case p.MatchString(s.Track):
				score += 2
				in["track"] = true
			case p.MatchString(s.searchDesc):
				score++
				in["description"] = true
				if ctx == "" {
					ctx = around(s.searchDesc, p.FindStringIndex(s.searchDesc), 90)
				}
			}
		}
		if len(pats) > 0 && score == 0 {
			continue
		}
		h := Hit{Session: s}
		if len(termPats) > 0 {
			who := strings.Join(append(s.Speakers, s.Track), " ")
			for i, p := range termPats {
				switch {
				case p.MatchString(s.searchTitle):
					score += 3
				case p.MatchString(who) || p.MatchString(s.searchDesc):
					score++
				default:
					continue
				}
				h.MatchedTerms = append(h.MatchedTerms, termNames[i])
			}
			if len(h.MatchedTerms) == 0 {
				continue
			}
		}
		if len(in) == 1 && in["description"] {
			h.Context = ctx
		}
		for _, f := range []string{"title", "speakers", "track", "description"} {
			if in[f] {
				h.MatchedIn = append(h.MatchedIn, f)
			}
		}
		hits = append(hits, scored{h, score})
	}
	total = len(hits)
	if len(hits) > limit {
		sort.SliceStable(hits, func(i, j int) bool { return hits[i].score > hits[j].score })
		hits = hits[:limit]
		sort.SliceStable(hits, func(i, j int) bool { return hits[i].h.start.Before(hits[j].h.start) })
	}
	for _, h := range hits {
		matches = append(matches, h.h)
	}
	return matches, total, nil
}

func around(text string, loc []int, n int) string {
	r := []rune(text)
	start := len([]rune(text[:loc[0]]))
	lo, hi := max(0, start-n), min(len(r), start+n)
	return strings.ReplaceAll("…"+string(r[lo:hi])+"…", "\n", " ")
}

// Find returns the session with the given ID.
func (a *Agenda) Find(id string) (Session, bool) {
	for _, s := range a.Sessions {
		if s.ID == id {
			return s, true
		}
	}
	return Session{}, false
}

// PlanEntry is one session of a checked plan.
type PlanEntry struct {
	ID    string `json:"id"`
	Date  string `json:"date"`
	Start string `json:"start"`
	End   string `json:"end"`
	Title string `json:"title"`
}

// Overlap is a pair of sessions in a plan that run at the same time.
type Overlap struct {
	First  PlanEntry `json:"first"`
	Second PlanEntry `json:"second"`
}

// PlanCheck is the result of CheckPlan.
type PlanCheck struct {
	OK       bool        `json:"ok"`
	Sessions []PlanEntry `json:"sessions"`
	Overlaps []Overlap   `json:"overlaps,omitempty"`
	NotFound []string    `json:"not_found,omitempty"`
}

// CheckPlan orders the sessions with the given IDs by time and reports every
// pair that overlaps.
func (a *Agenda) CheckPlan(ids []string) PlanCheck {
	var picked []Session
	out := PlanCheck{Sessions: []PlanEntry{}}
	for _, id := range ids {
		if s, ok := a.Find(id); ok {
			picked = append(picked, s)
		} else {
			out.NotFound = append(out.NotFound, id)
		}
	}
	sort.SliceStable(picked, func(i, j int) bool { return picked[i].start.Before(picked[j].start) })
	entry := func(s Session) PlanEntry {
		return PlanEntry{ID: s.ID, Date: s.Date, Start: s.Start, End: s.End, Title: s.Title}
	}
	for i, p := range picked {
		out.Sessions = append(out.Sessions, entry(p))
		for _, q := range picked[i+1:] {
			if q.start.Before(p.end) && p.start.Before(q.end) {
				out.Overlaps = append(out.Overlaps, Overlap{First: entry(p), Second: entry(q)})
			}
		}
	}
	out.OK = len(out.Overlaps) == 0 && len(out.NotFound) == 0
	return out
}
