/**
 * Created by Shaoke Xu on 6/25/17.
 */
var protractor = require('protractor');

function PageObject(){
  this.$campingDate = $("#campingDate");
  this.$lengthOfStay = $("#lengthOfStay");
  this.$searchAvailable = $('#search_avail');
  this.calendarLocator = '#calendar';
  this.next2WeeksLocator = '#calendar .weeknav.week2';
  this.dateRangeAvailabilityLocator = '#calendar_view_switch';
  this.availableLocator = '#calendar td.status.a.sat a';
}

module.exports = PageObject;
