const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = 3000;

// Middleware
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '..', 'public')));

// View engine
const expressLayouts = require('express-ejs-layouts');
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, '..', 'views'));
app.use(expressLayouts);
app.set('layout', 'layout');

// Initialize DB
const db = require('./db');
db.init();

// Routes
app.use('/api', require('./routes/api'));
app.use('/', require('./routes/web'));

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 LeadForge running on http://0.0.0.0:${PORT}`);
  console.log(`🌐 Public: http://152.55.176.8:${PORT}`);
});
