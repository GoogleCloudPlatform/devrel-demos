<script>
import axios from "axios";

export default {
  data() {
    return {
      subtitle: "Long before tabs vs spaces...",
      title: "Cats XOR Dogs?",
      apiUrl: "",
      catVotes: 0,
      dogVotes: 0,
      voteCatsMessage: "Vote for Cats",
      voteDogsMessage: "Dogs are better",
      redisStatus: "i'm the redis status",
    };
  },
  methods: {
    async incrementCatsVote() {
      const response = await axios.post(`/cats`);

      if (response.data.error) {
        this.catVotes = "not available";
        return;
      }

      this.catVotes = response.data.votes;
    },
    async incrementDogsVote() {
      const response = await axios.post(`/dogs`);

      if (response.data.error) {
        this.dogVotes = "not available";
        return;
      }

      this.dogVotes = response.data.votes;
    },
  },

  async mounted() {
    const responseRedis = await axios.get(`/redisStatus`);
    if (responseRedis.data.status) {
      this.redisStatus = "Connected to Redis";

      const responseCats = await axios.get(`/cats`);
      this.catVotes = responseCats.data.votes;

      const responseDogs = await axios.get(`/dogs`);
      this.dogVotes = responseDogs.data.votes;
    } else {
      this.redisStatus = "Unable to connect to Redis";
      this.catVotes = "not available";
      this.dogVotes = "not available";
    }
  },
};
</script>

<template>
  <header>
    <span>{{ subtitle }}</span>
    <h1>{{ title }}</h1>
    <div class="columns xs">
      <div id="cats">
        <div class="vote-count">{{ catVotes }}</div>
        <!-- <div class="starburst">test</div> -->
        <div
          class="starburst"
          :class="{ starburst_visible: catVotes > dogVotes }"
        >
          <img
            src="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/320/google/56/cat_1f408.png"
          />
        </div>
        <button @click="incrementCatsVote">
          {{ voteCatsMessage }}
        </button>
      </div>
      <div id="dogs">
        <div class="vote-count">{{ dogVotes }}</div>
        <div
          class="starburst"
          :class="{ starburst_visible: catVotes < dogVotes }"
        >
          <img
            src="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/google/346/dog_1f415.png"
          />
        </div>
        <button @click="incrementDogsVote">
          {{ voteDogsMessage }}
        </button>
      </div>
    </div>
    <div id="redisStatus">
      <p>{{ redisStatus }}</p>
    </div>
  </header>
</template>

<style>
:root {
  --blue: #0054a1;
}
html {
  height: 100%;
  font-family: Arial, Helvetica, sans-serif;
  color: var(--blue);
}
body {
  background: radial-gradient(
    51.73% 51.73% at 50% 50%,
    #f6fcff 33%,
    #c5e9fe 100%
  );
  height: 100%;
  margin: 0;
  background-repeat: no-repeat;
  background-attachment: fixed;
  text-align: center;
}
</style>
<style scoped>
.columns {
  display: flex;
  flex-direction: row;
  height: 100%;
  max-width: 800px;
  margin: 0 auto;
}
@media (max-width: 512px) {
  .columns.xs {
    flex-direction: column;
  }
}
.columns > * {
  flex: 1;
  margin-top: 5%;
}
button {
  border-radius: 32px;
  color: var(--blue);
  height: 64px;
  padding: 16px 24px;
  font-size: 20px;
  margin: 24px;
  transition: all 200ms;
  border: none;
  background: white;
}
button:hover {
  background: white;
  box-shadow: 0 2px 7px 0 rgba(0, 0, 0, 0.3);
}
button:active {
  border: 2px solid var(--blue) !important;
}
button[disabled] {
  border: 2px solid var(--blue) !important;
  background: var(--blue);
  color: white;
  pointer-events: none;
}
.vote-count {
  font-size: 36px;
  color: var(--blue);
  margin: 0 0 24px -8px;
}
#cats button {
  border: 2px solid #ea9942;
}
#dogs button {
  border: 2px solid #c77d5d;
}
#redisStatus {
  font-size: x-large;
}
img {
  width: 140px;
  /* margin-bottom: 24px; */
}
.starburst {
  /* thx to https://css-generators.com/starburst-shape/ */
  aspect-ratio: 1;
  width: 240px;
  margin: 0 auto;
  display: flex;
  justify-content: center; /* horz */
  align-items: center; /* vert */
}
.starburst_visible {
  background: #c5e9fe;
  clip-path: polygon(
    100% 50%,
    90.57% 60.87%,
    93.3% 75%,
    79.7% 79.7%,
    75% 93.3%,
    60.87% 90.57%,
    50% 100%,
    39.13% 90.57%,
    25% 93.3%,
    20.3% 79.7%,
    6.7% 75%,
    9.43% 60.87%,
    0% 50%,
    9.43% 39.13%,
    6.7% 25%,
    20.3% 20.3%,
    25% 6.7%,
    39.13% 9.43%,
    50% 0%,
    60.87% 9.43%,
    75% 6.7%,
    79.7% 20.3%,
    93.3% 25%,
    90.57% 39.13%
  );
}
</style>
