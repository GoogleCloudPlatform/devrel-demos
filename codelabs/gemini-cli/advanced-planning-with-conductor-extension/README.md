# Picker - Core Spinning Wheel

A simple, fun, and intuitive web application that helps you make decisions by spinning a wheel.

## 🎡 Features

- **Interactive Spinning Wheel**: Start the spinner with a single click and watch it go with smooth CSS animations.
- **Customizable Options**: Easily add, edit, or remove options inline. Each option is automatically assigned a vibrant random color.
- **Winner Announcement**: A clear modal displays the winning selection after a 3-second spin.
- **Desktop-First Design**: Optimized for a great experience on larger screens and mouse-based interactions.

## 🛠️ Tech Stack

- **Frontend**: [Vue.js 3](https://vuejs.org/) (Composition API)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Testing**: [Vitest](https://vitest.dev/)
- **Styling**: Vanilla CSS

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (latest LTS recommended)
- npm (comes with Node.js)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd picker
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

### Development

Start the development server:
```bash
npm run dev
```

### Build

Build the project for production:
```bash
npm run build
```

### Testing

Run the test suite:
```bash
npm run test
```

## 📂 Project Structure

- `src/components/`: Vue components (Spinner, OptionList, etc.)
- `src/composables/`: Shared logic (useSpin, useOptions)
- `conductor/`: Project management and technical documentation
