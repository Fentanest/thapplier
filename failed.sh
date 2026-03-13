#!/bin/bash
# Remove temporary failure states from coupon logs so they can be retried
sed -i '/Failed/d' coupon_logs/*.txt
sed -i '/Frequent/d' coupon_logs/*.txt
sed -i '/frequent/d' coupon_logs/*.txt
sed -i '/빈번한/d' coupon_logs/*.txt
sed -i '/횟수가 초과/d' coupon_logs/*.txt
sed -i '/Limit\/Rate/d' coupon_logs/*.txt
sed -i '/Paused/d' coupon_logs/*.txt
