#!/bin/bash
logrotate ~/.config/logrotate/hermes.conf --state ~/.config/logrotate/hermes.state 2>/dev/null
echo '{"wakeAgent": false}'
